from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel

from app.domain.entities import (
    ForecastResult,
    OrderResult,
    PurchaseProposal,
    PurchaseRequest,
    SupplierQuote,
)


class LLMProvider(Protocol):
    async def structured(
        self, messages: Sequence[dict[str, str]], schema: type[BaseModel]
    ) -> BaseModel: ...


class VoiceProvider(Protocol):
    async def transcribe(
        self, audio: AsyncIterator[bytes], *, language_code: str
    ) -> AsyncIterator[Any]: ...

    async def synthesize(self, text: str, *, language_code: str) -> AsyncIterator[bytes]: ...


class WhatsAppProvider(Protocol):
    async def send_text(self, recipient: str, body: str, *, idempotency_key: str) -> str: ...

    async def send_approval(
        self, recipient: str, proposal: dict, *, idempotency_key: str
    ) -> str: ...


class SupplierAdapter(Protocol):
    async def discover(self, request: PurchaseRequest) -> list[SupplierQuote]: ...

    async def quote(self, request: PurchaseRequest) -> SupplierQuote: ...

    async def counter_offer(
        self, quote: SupplierQuote, *, unit_price: float, quantity: float, idempotency_key: str
    ) -> SupplierQuote | None: ...

    async def place_order(
        self, proposal: PurchaseProposal, *, idempotency_key: str
    ) -> OrderResult: ...


class EventBus(Protocol):
    async def publish(self, event: Any) -> None: ...


class ForecastModel(Protocol):
    name: str

    def fit(self, rows: Any, target: Any) -> None: ...

    def predict(self, rows: Any, *, horizon_days: int) -> ForecastResult: ...


class IdempotencyStore(Protocol):
    async def reserve(self, scope: str, key: str, request_hash: str) -> bool: ...

    async def complete(self, scope: str, key: str, response: dict[str, Any]) -> None: ...


class TransactionExecutor(Protocol):
    async def execute(
        self,
        proposal: PurchaseProposal,
        *,
        approval_id: UUID,
        approval_token: str,
        idempotency_key: str,
    ) -> OrderResult: ...
