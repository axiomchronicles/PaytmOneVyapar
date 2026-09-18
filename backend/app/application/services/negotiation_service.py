from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities import PurchaseRequest, SupplierQuote


@dataclass(frozen=True)
class NegotiationConstraints:
    min_quantity: Decimal
    max_quantity: Decimal
    max_unit_price: Decimal
    allowed_supplier_ids: frozenset[str]
    max_rounds: int = 3
    timeout_seconds: int = 20


class NegotiationService:
    def validate_offer(
        self,
        quote: SupplierQuote,
        request: PurchaseRequest,
        constraints: NegotiationConstraints,
        *,
        round_number: int,
    ) -> tuple[bool, tuple[str, ...]]:
        failures: list[str] = []
        if round_number > constraints.max_rounds:
            failures.append("round_limit")
        if str(quote.supplier_id) not in constraints.allowed_supplier_ids:
            failures.append("supplier_not_allowed")
        if (
            request.quantity < constraints.min_quantity
            or request.quantity > constraints.max_quantity
        ):
            failures.append("quantity_out_of_bounds")
        if quote.available_quantity < request.quantity:
            failures.append("insufficient_supplier_inventory")
        if quote.unit_price > constraints.max_unit_price or quote.unit_price > request.max_price:
            failures.append("price_limit")
        if quote.delivery_at > request.delivery_deadline:
            failures.append("delivery_deadline")
        return not failures, tuple(failures)

    def counter_price(self, quote: SupplierQuote, request: PurchaseRequest) -> Decimal:
        if quote.unit_price <= request.target_price:
            return quote.unit_price
        midpoint = (quote.unit_price + request.target_price) / Decimal("2")
        return min(midpoint.quantize(Decimal("0.01")), request.max_price)
