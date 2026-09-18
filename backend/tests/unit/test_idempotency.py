import asyncio

import pytest

from app.core.errors import ConflictError
from app.infrastructure.idempotency import MemoryIdempotencyStore


@pytest.mark.asyncio
async def test_only_one_concurrent_idempotency_reservation_wins() -> None:
    store = MemoryIdempotencyStore()
    outcomes = await asyncio.gather(
        *(store.reserve("orders", "same-key", "same-hash") for _ in range(8))
    )
    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 7


@pytest.mark.asyncio
async def test_idempotency_key_cannot_change_request() -> None:
    store = MemoryIdempotencyStore()
    assert await store.reserve("orders", "key-12345", "hash-one")
    with pytest.raises(ConflictError):
        await store.reserve("orders", "key-12345", "hash-two")
