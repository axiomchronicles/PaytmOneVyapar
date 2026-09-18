import html
from decimal import Decimal

from app.domain.entities import PurchaseProposal


def approval_message(proposal: PurchaseProposal, approval_id: str) -> dict[str, str]:
    """Serializes a proposal into a dictionary payload for the Telegram provider."""
    return {
        "approval_id": approval_id,
        "sku": proposal.sku,
        "quantity": str(proposal.quantity),
        "unit": proposal.unit,
        "unit_price": str(proposal.unit_price),
        "total_amount": str(proposal.total_amount.quantize(Decimal("0.01"))),
        "currency": proposal.currency,
        "delivery_at": proposal.delivery_at.isoformat() if proposal.delivery_at else "",
    }


def format_decision_confirmation(
    sku: str,
    action: str,
    *,
    quantity: str | None = None,
    total_amount: str | None = None,
    currency: str = "INR",
) -> str:
    """Format an updated message text after a decision is made."""
    safe_sku = html.escape(sku)
    if action == "APPROVE":
        amt_str = f" for <b>{currency} {total_amount}</b>" if total_amount else ""
        return (
            f"✅ <b>PURCHASE ORDER APPROVED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Item:</b> {safe_sku}\n"
            f"Order has been confirmed and placed with supplier{amt_str}."
        )
    elif action == "REJECT":
        return (
            f"❌ <b>PURCHASE ORDER DECLINED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Item:</b> {safe_sku}\n"
            f"Proposal was rejected. No order will be placed."
        )
    elif action == "MODIFY":
        qty_str = f" (target quantity: {quantity})" if quantity else ""
        return (
            f"✏️ <b>PURCHASE ORDER MODIFICATION REQUESTED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Item:</b> {safe_sku}{qty_str}\n"
            f"A revised proposal is being prepared."
        )
    return f"ℹ️ Order status updated: {action}"
