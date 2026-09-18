import asyncio
import json

from conftest import MERCHANT_ID
from sqlalchemy import select

from app.api.v1.websocket import RealtimeHub
from app.domain.events import EventType
from app.infrastructure.db.models import OutboxEvent
from app.infrastructure.events.bus import RedisEventBus
from app.infrastructure.events.outbox import OutboxPublisher
from app.infrastructure.events.realtime import RedisRealtimeBridge


class _FakePubSub:
    def __init__(self, queue: asyncio.Queue) -> None:
        self.queue = queue

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def subscribe(self, channel: str) -> None:
        return None

    async def listen(self):
        while True:
            yield {"type": "message", "data": await self.queue.get()}


class _FakeRedis:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()

    async def publish(self, channel: str, payload: str) -> int:
        await self.queue.put(payload.encode())
        return 1

    def pubsub(self) -> _FakePubSub:
        return _FakePubSub(self.queue)


class _Socket:
    def __init__(self) -> None:
        self.events: asyncio.Queue = asyncio.Queue()
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, value: dict) -> None:
        await self.events.put(value)


class _UnavailableBus:
    async def publish(self, event) -> None:
        raise ConnectionError("redis unavailable")


async def test_database_outbox_redis_bridge_reaches_merchant_client(db_factory) -> None:
    async with db_factory() as session, session.begin():
        row = OutboxEvent(
            merchant_id=MERCHANT_ID,
            aggregate_type="order",
            aggregate_id=MERCHANT_ID,
            event_type=EventType.ORDER_EXECUTED,
            correlation_id="request-123",
            trace_id="trace-123",
            payload={"order_id": str(MERCHANT_ID), "status": "CONFIRMED"},
        )
        session.add(row)
        await session.flush()
        event_id = row.id

    redis = _FakeRedis()
    hub = RealtimeHub()
    socket = _Socket()
    await hub.connect(MERCHANT_ID, socket)
    bridge = RedisRealtimeBridge(redis, hub)
    task = asyncio.create_task(bridge.run())
    await asyncio.sleep(0)
    async with db_factory() as session, session.begin():
        assert await OutboxPublisher(session, RedisEventBus(redis)).publish_batch() == 1
    event = await asyncio.wait_for(socket.events.get(), timeout=1)
    bridge.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert event["event_id"] == str(event_id)
    assert event["event_type"] == "ORDER_EXECUTED"
    assert event["version"] == 1
    assert event["payload"]["status"] == "CONFIRMED"


async def test_redis_failure_keeps_outbox_pending(db_factory) -> None:
    async with db_factory() as session, session.begin():
        row = OutboxEvent(
            merchant_id=MERCHANT_ID,
            aggregate_type="inventory",
            aggregate_id=MERCHANT_ID,
            event_type=EventType.INVENTORY_UPDATED,
            payload={"quantity_on_hand": "4"},
        )
        session.add(row)
        await session.flush()
        event_id = row.id
    async with db_factory() as session, session.begin():
        assert await OutboxPublisher(session, _UnavailableBus()).publish_batch() == 0
    async with db_factory() as session:
        stored = await session.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert stored is not None
        assert stored.published_at is None
        assert stored.attempts == 1
        assert json.loads(json.dumps(stored.payload))["quantity_on_hand"] == "4"
