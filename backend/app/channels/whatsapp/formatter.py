from decimal import Decimal

from app.domain.entities import PurchaseProposal


def approval_message(proposal: PurchaseProposal, approval_id: str) -> dict[str, str]:
    return {
        "approval_id": approval_id,
        "sku": proposal.sku,
        "quantity": str(proposal.quantity),
        "unit": proposal.unit,
        "unit_price": str(proposal.unit_price),
        "total_amount": str(proposal.total_amount.quantize(Decimal("0.01"))),
        "currency": proposal.currency,
        "delivery_at": proposal.delivery_at.isoformat(),
    }
