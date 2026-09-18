import asyncio
import hashlib
from typing import Any

import httpx

from app.core.errors import ProviderAuthenticationError, ProviderError, ProviderTimeoutError
from app.domain.entities import OrderResult, PurchaseProposal, PurchaseRequest, SupplierQuote


class RestSupplierAdapter:
    def __init__(
        self, endpoint: str, client: httpx.AsyncClient, *, auth_token: str | None = None
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.client = client
        self.auth_token = auth_token

    async def discover(self, request: PurchaseRequest) -> list[SupplierQuote]:
        return [await self.quote(request)]

    async def quote(self, request: PurchaseRequest) -> SupplierQuote:
        request_key = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        data = await self._post("/quotes", self._purchase_request(request), request_key)
        return SupplierQuote.model_validate(data)

    async def counter_offer(
        self, quote: SupplierQuote, *, unit_price: float, quantity: float, idempotency_key: str
    ) -> SupplierQuote | None:
        data = await self._post(
            "/counter-offers",
            {"quote_id": quote.quote_id, "unit_price": unit_price, "quantity": quantity},
            idempotency_key,
        )
        return SupplierQuote.model_validate(data) if data.get("accepted") else None

    async def place_order(self, proposal: PurchaseProposal, *, idempotency_key: str) -> OrderResult:
        data = await self._post("/orders", proposal.canonical_payload(), idempotency_key)
        return OrderResult.model_validate(data)

    @staticmethod
    def _purchase_request(request: PurchaseRequest) -> dict[str, Any]:
        return request.model_dump(mode="json", exclude={"request_id"})

    async def _post(self, path: str, payload: dict, idempotency_key: str) -> dict:
        headers = {"Idempotency-Key": idempotency_key}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        for attempt in range(3):
            try:
                response = await self.client.post(
                    f"{self.endpoint}{path}", json=payload, headers=headers
                )
                if response.status_code in {401, 403}:
                    raise ProviderAuthenticationError("Supplier authentication failed")
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                if attempt == 2:
                    raise ProviderTimeoutError("Supplier request timed out") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or attempt == 2:
                    raise ProviderError(
                        "Supplier request failed",
                        details={"status": exc.response.status_code},
                    ) from exc
            await asyncio.sleep(0.25 * (2**attempt))
        raise ProviderError("Supplier request failed")
