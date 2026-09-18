from decimal import Decimal

from app.domain.entities import InventorySnapshot, PurchaseProposal, RiskResult, SupplierQuote


class RiskService:
    def evaluate(
        self,
        *,
        inventory: InventorySnapshot,
        proposal: PurchaseProposal,
        quote: SupplierQuote,
        spending_limit: Decimal,
        supplier_trust_score: Decimal = Decimal("1"),
        duplicate_order: bool = False,
    ) -> RiskResult:
        checks = {
            "positive_quantity": proposal.quantity > 0,
            "inventory_consistent": inventory.quantity_on_hand >= 0,
            "supplier_inventory": quote.available_quantity >= proposal.quantity,
            "supplier_trusted": supplier_trust_score >= Decimal("0.6"),
            "spending_limit": proposal.total_amount <= spending_limit,
            "not_duplicate": not duplicate_order,
            "price_consistent": proposal.unit_price == quote.unit_price,
        }
        return RiskResult(
            passed=all(checks.values()),
            reasons=tuple(name for name, passed in checks.items() if not passed),
            checks=checks,
        )
