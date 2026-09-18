import asyncio

import structlog

from app.domain.events import DomainEvent
from app.infrastructure.redis.pubsub import RedisPubSub

logger = structlog.get_logger()


class RedisRealtimeBridge:
    """Projects durable outbox publications from Redis to connected merchants."""

    def __init__(self, redis, hub) -> None:
        self._pubsub = RedisPubSub(redis)
        self._hub = hub
        self._stopped = False

    async def run(self) -> None:
        retry = 0
        while not self._stopped:
            try:
                async for raw in self._pubsub.subscribe():
                    retry = 0
                    event = DomainEvent.model_validate(raw)
                    if event.merchant_id is None:
                        continue
                    await self._hub.publish(event.merchant_id, event.model_dump(mode="json"))
                    if self._stopped:
                        return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                retry = min(retry + 1, 6)
                logger.warning(
                    "realtime_bridge_disconnected",
                    error_type=type(exc).__name__,
                    retry_seconds=2 ** (retry - 1),
                )
                await asyncio.sleep(2 ** (retry - 1))

    def stop(self) -> None:
        self._stopped = True
