from app.application.services.negotiation_service import NegotiationConstraints, NegotiationService
from app.core.errors import SupplierUnavailableError
from app.domain.contracts import SupplierAdapter
from app.domain.entities import PurchaseRequest, SupplierQuote


class ProcurementService:
    def __init__(self, suppliers: list[SupplierAdapter], negotiation: NegotiationService) -> None:
        self.suppliers = suppliers
        self.negotiation = negotiation

    async def discover(self, request: PurchaseRequest) -> list[SupplierQuote]:
        quotes: list[SupplierQuote] = []
        for supplier in self.suppliers:
            try:
                quotes.extend(await supplier.discover(request))
            except SupplierUnavailableError:
                continue
        if not quotes:
            raise SupplierUnavailableError("No supplier returned a usable quote")
        return sorted(quotes, key=lambda quote: (quote.unit_price, quote.delivery_at))

    async def negotiate(
        self,
        adapter: SupplierAdapter,
        quote: SupplierQuote,
        request: PurchaseRequest,
        constraints: NegotiationConstraints,
        *,
        idempotency_key: str,
    ) -> SupplierQuote:
        accepted, _ = self.negotiation.validate_offer(quote, request, constraints, round_number=1)
        if accepted:
            return quote
        counter = self.negotiation.counter_price(quote, request)
        revised = await adapter.counter_offer(
            quote,
            unit_price=float(counter),
            quantity=float(request.quantity),
            idempotency_key=idempotency_key,
        )
        if revised is None:
            raise SupplierUnavailableError("Supplier rejected the constrained counter offer")
        accepted, reasons = self.negotiation.validate_offer(
            revised, request, constraints, round_number=2
        )
        if not accepted:
            raise SupplierUnavailableError(
                f"Supplier offer violates constraints: {', '.join(reasons)}"
            )
        return revised
