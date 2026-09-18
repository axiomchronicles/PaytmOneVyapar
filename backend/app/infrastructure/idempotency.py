import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.infrastructure.db.models import IdempotencyKey


class SQLIdempotencyStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def reserve(self, scope: str, key: str, request_hash: str) -> bool:
        statement = (
            insert(IdempotencyKey)
            .values(scope=scope, key=key, request_hash=request_hash)
            .on_conflict_do_nothing(index_elements=["scope", "key"])
            .returning(IdempotencyKey.id)
        )
        return (await self.session.scalar(statement)) is not None

    async def complete(self, scope: str, key: str, response: dict[str, Any]) -> None:
        row = await self.session.scalar(
            select(IdempotencyKey)
            .where(IdempotencyKey.scope == scope, IdempotencyKey.key == key)
            .with_for_update()
        )
        if row is None:
            raise ConflictError("Idempotency reservation does not exist")
        row.status = "COMPLETED"
        row.response = response
        await self.session.flush()


class MemoryIdempotencyStore:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], tuple[str, dict[str, Any] | None]] = {}
        self._lock = asyncio.Lock()

    async def reserve(self, scope: str, key: str, request_hash: str) -> bool:
        async with self._lock:
            identity = (scope, key)
            if identity in self._entries:
                if self._entries[identity][0] != request_hash:
                    raise ConflictError("Idempotency key was reused with a different request")
                return False
            self._entries[identity] = (request_hash, None)
            return True

    async def complete(self, scope: str, key: str, response: dict[str, Any]) -> None:
        async with self._lock:
            identity = (scope, key)
            request_hash, _ = self._entries[identity]
            self._entries[identity] = (request_hash, response)
