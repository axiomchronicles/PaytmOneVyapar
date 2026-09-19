import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4, uuid5

from app.a2a.schemas import (
    A2AEnvelope,
    A2AIntent,
    CounterOfferPayload,
    OfferDecisionPayload,
    OrderConfirmationPayload,
    PurchaseRequestPayload,
    QuotePayload,
)
from app.a2a.signing import sign_envelope, verify_envelope
from app.core.errors import SupplierUnavailableError
from app.core.security import utc_now
from app.domain.entities import OrderResult, PurchaseProposal, PurchaseRequest, SupplierQuote
from app.domain.enums import OrderStatus

MOCK_NAMESPACE = UUID("c0ffee00-0000-4000-8000-000000000001")
BUYER_AGENT_ID = UUID("11111111-1111-4111-8111-111111111111")


class A2ARecorder(Protocol):
    async def record(
        self,
        envelope: A2AEnvelope,
        *,
        direction: str,
        merchant_id: UUID,
        supplier_id: UUID,
    ) -> None: ...


@dataclass(frozen=True)
class CatalogItem:
    sku: str
    available_quantity: Decimal
    unit_price: Decimal
    lead_time_days: int = 1


class MockSupplierAdapter:
    def __init__(
        self,
        *,
        name: str = "Bharat Beverage Wholesale",
        catalog: dict[str, CatalogItem] | None = None,
        latency_seconds: float = 0.01,
        fail_every: int = 0,
        signing_secret: str | None = None,
        buyer_agent_id: UUID = BUYER_AGENT_ID,
        message_recorder: A2ARecorder | None = None,
    ) -> None:
        self.name = name
        self.supplier_id = uuid5(MOCK_NAMESPACE, name)
        self.buyer_agent_id = buyer_agent_id
        self.message_recorder = message_recorder
        self.signing_secret = signing_secret or "development-a2a-secret-change-me"  # noqa: S105
        self.catalog = catalog or {
            "COLD-COLA-300": CatalogItem("COLD-COLA-300", Decimal("240"), Decimal("470.00"), 1),
            "TATA-SALT-1KG": CatalogItem("TATA-SALT-1KG", Decimal("500"), Decimal("26.00"), 1),
            "FORTUNE-OIL-1L": CatalogItem("FORTUNE-OIL-1L", Decimal("180"), Decimal("142.00"), 1),
            "AASHIRVAAD-ATTA-5KG": CatalogItem("AASHIRVAAD-ATTA-5KG", Decimal("120"), Decimal("220.00"), 1),
            "MAGGI-70G": CatalogItem("MAGGI-70G", Decimal("600"), Decimal("12.00"), 1),
            "PARLE-G-100G": CatalogItem("PARLE-G-100G", Decimal("300"), Decimal("10.00"), 1),
            "AMUL-BUTTER-100G": CatalogItem("AMUL-BUTTER-100G", Decimal("150"), Decimal("56.00"), 1),
            "DETTOL-SOAP-75G": CatalogItem("DETTOL-SOAP-75G", Decimal("200"), Decimal("40.00"), 1),
        }
        self.latency_seconds = latency_seconds
        self.fail_every = fail_every
        self._calls = 0
        self._orders: dict[str, OrderResult] = {}
        self._quotes: dict[str, SupplierQuote] = {}
        self._message_results: dict[str, A2AEnvelope] = {}
        self._quote_correlations: dict[str, UUID] = {}
        self._quote_merchants: dict[str, UUID] = {}
        self._pending_messages: dict[str, list[tuple[A2AEnvelope, str, UUID]]] = {}

    async def discover(self, request: PurchaseRequest) -> list[SupplierQuote]:
        return [await self.quote(request)]

    async def quote(self, request: PurchaseRequest) -> SupplierQuote:
        payload = PurchaseRequestPayload(**request.model_dump(exclude={"request_id"}))
        request_scope = request.request_id or str(request.quantity)
        response = await self._exchange(
            A2AIntent.PURCHASE_REQUEST,
            payload.model_dump(mode="json", exclude={"intent"}),
            idempotency_key=(
                f"quote:{request.merchant_id}:{request.sku}:{request_scope}:{request.quantity}"
            ),
            merchant_id=request.merchant_id,
        )
        if response.intent != A2AIntent.QUOTE:
            raise SupplierUnavailableError("Mock supplier rejected the purchase request")
        typed = QuotePayload.model_validate({"intent": response.intent, **response.payload})
        quote = SupplierQuote(
            supplier_id=self.supplier_id,
            supplier_name=self.name,
            **typed.model_dump(exclude={"intent"}),
        )
        self._quote_correlations[quote.quote_id] = response.correlation_id
        self._quote_merchants[quote.quote_id] = request.merchant_id
        return quote

    async def counter_offer(
        self, quote: SupplierQuote, *, unit_price: float, quantity: float, idempotency_key: str
    ) -> SupplierQuote | None:
        payload = CounterOfferPayload(
            quote_id=quote.quote_id,
            quantity=Decimal(str(quantity)),
            unit_price=Decimal(str(unit_price)),
            round=1,
        )
        response = await self._exchange(
            A2AIntent.COUNTER_OFFER,
            payload.model_dump(mode="json", exclude={"intent"}),
            idempotency_key=idempotency_key,
            merchant_id=self._quote_merchants.get(quote.quote_id),
            correlation_id=self._quote_correlations.get(quote.quote_id),
        )
        if response.intent == A2AIntent.OFFER_REJECTED:
            return None
        typed = QuotePayload.model_validate({"intent": response.intent, **response.payload})
        return SupplierQuote(
            supplier_id=self.supplier_id,
            supplier_name=self.name,
            **typed.model_dump(exclude={"intent"}),
        )

    async def place_order(self, proposal: PurchaseProposal, *, idempotency_key: str) -> OrderResult:
        if idempotency_key in self._orders:
            return self._orders[idempotency_key]
        payload = OfferDecisionPayload(
            intent=A2AIntent.OFFER_ACCEPTED,
            quote_id=proposal.quote_id,
            proposal=proposal.canonical_payload(),
        )
        response = await self._exchange(
            A2AIntent.OFFER_ACCEPTED,
            payload.model_dump(mode="json", exclude={"intent"}),
            idempotency_key=idempotency_key,
            merchant_id=proposal.merchant_id,
            correlation_id=self._quote_correlations.get(proposal.quote_id),
            defer_recording=True,
        )
        confirmation = OrderConfirmationPayload.model_validate(
            {"intent": response.intent, **response.payload}
        )
        result = OrderResult(
            order_id=confirmation.order_id,
            status=OrderStatus.CONFIRMED,
            supplier_confirmation=confirmation.supplier_reference,
        )
        self._orders[idempotency_key] = result
        return result

    async def handle_envelope(self, envelope: A2AEnvelope) -> A2AEnvelope:
        verify_envelope(
            envelope,
            secret=self.signing_secret,
            expected_receiver_id=str(self.supplier_id),
        )
        if envelope.idempotency_key in self._message_results:
            return self._message_results[envelope.idempotency_key]
        await self._delay_or_fail()
        if envelope.intent == A2AIntent.PURCHASE_REQUEST:
            request_payload = PurchaseRequestPayload.model_validate(
                {"intent": envelope.intent, **envelope.payload}
            )
            quote = self._quote_from_payload(request_payload)
            response_intent = A2AIntent.QUOTE
            response_payload = self._quote_payload(quote)
        elif envelope.intent == A2AIntent.COUNTER_OFFER:
            counter = CounterOfferPayload.model_validate(
                {"intent": envelope.intent, **envelope.payload}
            )
            original = self._quotes.get(counter.quote_id)
            if original is None:
                raise SupplierUnavailableError("Unknown or expired quote")
            floor = (original.unit_price * Decimal("0.94")).quantize(Decimal("0.01"))
            if counter.unit_price < floor or counter.quantity > original.available_quantity:
                response_intent = A2AIntent.OFFER_REJECTED
                response_payload = {"quote_id": counter.quote_id, "reason": "outside_constraints"}
            else:
                revised = original.model_copy(update={"unit_price": max(counter.unit_price, floor)})
                self._quotes[revised.quote_id] = revised
                response_intent = A2AIntent.QUOTE
                response_payload = self._quote_payload(revised)
        elif envelope.intent == A2AIntent.OFFER_ACCEPTED:
            accepted = OfferDecisionPayload.model_validate(
                {"intent": envelope.intent, **envelope.payload}
            )
            proposal = PurchaseProposal.model_validate(accepted.proposal.model_dump())
            quote = self._quotes.get(accepted.quote_id)
            item = self.catalog.get(proposal.sku)
            if quote is None or item is None or item.available_quantity < proposal.quantity:
                raise SupplierUnavailableError("Supplier inventory changed before execution")
            order_id = uuid5(MOCK_NAMESPACE, envelope.idempotency_key)
            response_intent = A2AIntent.ORDER_CONFIRMATION
            response_payload = OrderConfirmationPayload(
                order_id=order_id,
                supplier_reference=(
                    f"BWW-{hashlib.sha256(envelope.idempotency_key.encode()).hexdigest()[:10].upper()}"
                ),
                expected_delivery_at=quote.delivery_at,
            ).model_dump(mode="json", exclude={"intent"})
        else:
            raise SupplierUnavailableError(f"Unsupported supplier intent {envelope.intent}")
        response = self._envelope(
            intent=response_intent,
            payload=response_payload,
            sender=self.supplier_id,
            receiver=envelope.sender_agent_id,
            correlation_id=envelope.correlation_id,
            idempotency_key=f"response:{envelope.idempotency_key}",
        )
        self._message_results[envelope.idempotency_key] = response
        return response

    def advertised_inventory(self) -> list[dict[str, str]]:
        return [
            {
                "sku": item.sku,
                "available_quantity": str(item.available_quantity),
                "unit_price": str(item.unit_price),
            }
            for item in self.catalog.values()
        ]

    async def _exchange(
        self,
        intent: A2AIntent,
        payload: dict,
        *,
        idempotency_key: str,
        merchant_id: UUID | None,
        correlation_id: UUID | None = None,
        defer_recording: bool = False,
    ) -> A2AEnvelope:
        request = self._envelope(
            intent=intent,
            payload=payload,
            sender=self.buyer_agent_id,
            receiver=self.supplier_id,
            correlation_id=correlation_id or uuid5(MOCK_NAMESPACE, idempotency_key),
            idempotency_key=idempotency_key,
        )
        if merchant_id is not None and defer_recording:
            self._pending_messages.setdefault(idempotency_key, []).append(
                (request, "OUTBOUND", merchant_id)
            )
        elif merchant_id is not None and self.message_recorder is not None:
            await self.message_recorder.record(
                request,
                direction="OUTBOUND",
                merchant_id=merchant_id,
                supplier_id=self.supplier_id,
            )
        response = await self.handle_envelope(request)
        verify_envelope(
            response,
            secret=self.signing_secret,
            expected_receiver_id=str(self.buyer_agent_id),
        )
        if merchant_id is not None and defer_recording:
            self._pending_messages.setdefault(idempotency_key, []).append(
                (response, "INBOUND", merchant_id)
            )
        elif merchant_id is not None and self.message_recorder is not None:
            await self.message_recorder.record(
                response,
                direction="INBOUND",
                merchant_id=merchant_id,
                supplier_id=self.supplier_id,
            )
        return response

    def correlation_id_for_quote(self, quote_id: str) -> UUID | None:
        return self._quote_correlations.get(quote_id)

    def pop_pending_messages(self, idempotency_key: str) -> list[tuple[A2AEnvelope, str, UUID]]:
        return self._pending_messages.pop(idempotency_key, [])

    def _envelope(
        self,
        *,
        intent: A2AIntent,
        payload: dict,
        sender: UUID,
        receiver: UUID,
        correlation_id: UUID,
        idempotency_key: str,
    ) -> A2AEnvelope:
        now = utc_now()
        envelope = A2AEnvelope(
            message_id=uuid4(),
            correlation_id=correlation_id,
            trace_id=hashlib.sha256(idempotency_key.encode()).hexdigest()[:32],
            sender_agent_id=sender,
            receiver_agent_id=receiver,
            intent=intent,
            timestamp=now,
            expires_at=now + timedelta(minutes=5),
            nonce=secrets.token_urlsafe(18),
            payload=payload,
            signature="0" * 64,
            idempotency_key=idempotency_key,
        )
        return envelope.model_copy(
            update={"signature": sign_envelope(envelope, self.signing_secret)}
        )

    @staticmethod
    def _quote_payload(quote: SupplierQuote) -> dict:
        return QuotePayload(
            quote_id=quote.quote_id,
            sku=quote.sku,
            available_quantity=quote.available_quantity,
            unit_price=quote.unit_price,
            currency=quote.currency,
            delivery_at=quote.delivery_at,
            expires_at=quote.expires_at,
        ).model_dump(mode="json", exclude={"intent"})

    def _quote_from_payload(self, request: PurchaseRequestPayload) -> SupplierQuote:
        item = self.catalog.get(request.sku)
        if item is None or item.available_quantity < request.quantity:
            raise SupplierUnavailableError(f"{self.name} cannot fulfill {request.sku}")
        now = utc_now()
        identity = f"{request.merchant_id}:{request.sku}:{request.quantity}:{now.date()}"
        quote = SupplierQuote(
            supplier_id=self.supplier_id,
            supplier_name=self.name,
            sku=request.sku,
            available_quantity=item.available_quantity,
            unit_price=item.unit_price,
            delivery_at=now + timedelta(days=item.lead_time_days),
            quote_id=f"mock-{hashlib.sha256(identity.encode()).hexdigest()[:16]}",
            expires_at=now + timedelta(minutes=15),
        )
        self._quotes[quote.quote_id] = quote
        return quote

    async def _delay_or_fail(self) -> None:
        await asyncio.sleep(self.latency_seconds)
        self._calls += 1
        if self.fail_every and self._calls % self.fail_every == 0:
            raise SupplierUnavailableError("Deterministic mock supplier outage")
