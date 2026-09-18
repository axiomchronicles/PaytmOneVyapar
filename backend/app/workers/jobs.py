from app.infrastructure.db.session import get_session_factory
from app.infrastructure.events.bus import RedisEventBus
from app.infrastructure.events.outbox import OutboxPublisher


async def publish_outbox(ctx) -> int:
    async with get_session_factory()() as session, session.begin():
        return await OutboxPublisher(session, RedisEventBus(ctx["redis"])).publish_batch()
