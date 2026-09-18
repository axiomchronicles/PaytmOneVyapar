from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid5

from app.agents.services import WorkflowServices
from app.agents.state import PurchaseWorkflowState
from app.domain.entities import InventorySnapshot, PurchaseProposal, SupplierQuote

PROPOSAL_NAMESPACE = UUID("c0ffee00-0000-4000-8000-000000000002")


def risk_check(state: PurchaseWorkflowState, services: WorkflowServices) -> dict:
    quote = SupplierQuote.model_validate(state["selected_supplier"])
    revision = state.get("proposal_revision", 1)
    proposal = PurchaseProposal(
        proposal_id=uuid5(PROPOSAL_NAMESPACE, f"{state['request_id']}:{revision}"),
        merchant_id=UUID(state["merchant_id"]),
        store_id=UUID(state["store_id"]),
        supplier_id=quote.supplier_id,
        sku=state["sku"],
        quantity=Decimal(str(state["required_quantity"])),
        unit=state["unit"],
        unit_price=quote.unit_price,
        delivery_at=quote.delivery_at,
        quote_id=quote.quote_id,
    )
    inventory = InventorySnapshot(
        sku=state["sku"],
        quantity_on_hand=Decimal(str(state["inventory_snapshot"]["quantity_on_hand"])),
        reorder_point=Decimal(str(state["inventory_snapshot"]["reorder_point"])),
        captured_at=datetime.fromisoformat(state["inventory_snapshot"]["captured_at"]),
    )
    result = services.risk.evaluate(
        inventory=inventory,
        proposal=proposal,
        quote=quote,
        spending_limit=Decimal(str(state["spending_limit"])),
    )
    return {
        "risk_result": result.model_dump(mode="json"),
        "failure_reason": "" if result.passed else f"risk_failed:{','.join(result.reasons)}",
    }
