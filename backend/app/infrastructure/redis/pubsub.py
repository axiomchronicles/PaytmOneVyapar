import json
from collections.abc import AsyncIterator

from redis.asyncio import Redis


class RedisPubSub:
    def __init__(self, redis: Redis, *, channel: str = "vyapaar:events") -> None:
        self.redis = redis
        self.channel = channel

    async def publish(self, event: dict) -> None:
        await self.redis.publish(self.channel, json.dumps(event, default=str))

    async def subscribe(self) -> AsyncIterator[dict]:
        async with self.redis.pubsub() as pubsub:
            await pubsub.subscribe(self.channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
