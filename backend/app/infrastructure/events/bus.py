from redis.asyncio import Redis

from app.domain.events import DomainEvent
from app.infrastructure.redis.pubsub import RedisPubSub


class RedisEventBus:
    def __init__(self, redis: Redis) -> None:
        self.pubsub = RedisPubSub(redis)

    async def publish(self, event: DomainEvent) -> None:
        await self.pubsub.publish(event.model_dump(mode="json"))
