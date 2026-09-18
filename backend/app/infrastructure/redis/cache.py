import json
from typing import Any

from redis.asyncio import Redis


class RedisCache:
    def __init__(self, redis: Redis, *, prefix: str = "vyapaar") -> None:
        self.redis = redis
        self.prefix = prefix

    async def get(self, key: str) -> Any | None:
        value = await self.redis.get(f"{self.prefix}:cache:{key}")
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, *, ttl_seconds: int = 300) -> None:
        await self.redis.set(
            f"{self.prefix}:cache:{key}",
            json.dumps(value, separators=(",", ":"), default=str),
            ex=ttl_seconds,
        )

    async def delete(self, key: str) -> None:
        await self.redis.delete(f"{self.prefix}:cache:{key}")
