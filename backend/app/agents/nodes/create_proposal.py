from decimal import Decimal
from uuid import UUID, uuid5

from app.agents.nodes.risk_check import PROPOSAL_NAMESPACE
from app.agents.services import WorkflowServices
from app.agents.state import PurchaseWorkflowState
from app.core.security import canonical_order_hash
from app.domain.entities import PurchaseProposal, SupplierQuote


async def create_proposal(state: PurchaseWorkflowState, services: WorkflowServices) -> dict:
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
    approval, token = await services.approval_authority.request(proposal)
    payload = proposal.canonical_payload()
    return {
        "proposal": payload,
        "order_hash": canonical_order_hash(payload),
        "approval_status": "PENDING",
        "approval_id": str(approval.approval_id),
        "approval_token": token,
    }
