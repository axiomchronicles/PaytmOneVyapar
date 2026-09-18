from redis.asyncio import Redis

from app.core.errors import RateLimitError


class RedisRateLimiter:
    def __init__(self, redis: Redis, *, prefix: str = "vyapaar:rate") -> None:
        self.redis = redis
        self.prefix = prefix

    async def check(self, identity: str, *, limit: int, window_seconds: int) -> int:
        key = f"{self.prefix}:{identity}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            count, _ = await pipe.execute()
        if count > limit:
            raise RateLimitError("Request rate limit exceeded")
        return limit - count
