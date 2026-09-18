import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis

from app.core.errors import ConflictError

_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


class RedisLockManager:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @asynccontextmanager
    async def acquire(self, name: str, *, ttl_seconds: int = 30) -> AsyncIterator[None]:
        token = secrets.token_urlsafe(24)
        acquired = await self.redis.set(f"lock:{name}", token, ex=ttl_seconds, nx=True)
        if not acquired:
            raise ConflictError("Another operation is already processing this resource")
        try:
            yield
        finally:
            await self.redis.eval(_RELEASE_SCRIPT, 1, f"lock:{name}", token)
