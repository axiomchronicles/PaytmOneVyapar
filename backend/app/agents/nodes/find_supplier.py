from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.agents.services import WorkflowServices
from app.agents.state import PurchaseWorkflowState
from app.agents.tools.supplier_tools import collect_quotes
from app.domain.entities import PurchaseRequest


async def find_supplier(state: PurchaseWorkflowState, services: WorkflowServices) -> dict:
    request = PurchaseRequest(
        request_id=state["request_id"],
        sku=state["sku"],
        quantity=Decimal(str(state["required_quantity"])),
        unit=state["unit"],
        target_price=Decimal(str(state["target_price"])),
        max_price=Decimal(str(state["max_price"])),
        delivery_deadline=datetime.fromisoformat(state["delivery_requirement"]),
        merchant_id=UUID(state["merchant_id"]),
        store_id=UUID(state["store_id"]),
    )
    attempted = set(state.get("attempted_supplier_ids", []))
    quotes = [
        quote
        for quote in await collect_quotes(services.suppliers, request)
        if str(quote.supplier_id) not in attempted
    ]
    if not quotes:
        return {"candidate_suppliers": [], "failure_reason": "supplier_unavailable"}
    return {
        "candidate_suppliers": [quote.model_dump(mode="json") for quote in quotes],
        "failure_reason": "",
    }
