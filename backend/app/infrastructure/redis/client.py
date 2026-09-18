from redis.asyncio import Redis

from app.core.errors import RedisError


class RedisManager:
    def __init__(self, url: str) -> None:
        self.client = Redis.from_url(url, decode_responses=False)

    async def health(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception as exc:
            raise RedisError("Redis health check failed") from exc

    async def close(self) -> None:
        await self.client.aclose()
