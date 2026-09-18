from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.agents.services import WorkflowServices
from app.agents.state import PurchaseWorkflowState
from app.application.services.negotiation_service import NegotiationConstraints
from app.domain.entities import PurchaseRequest, SupplierQuote


async def negotiate(state: PurchaseWorkflowState, services: WorkflowServices) -> dict:
    request = PurchaseRequest(
        sku=state["sku"],
        quantity=Decimal(str(state["required_quantity"])),
        unit=state["unit"],
        target_price=Decimal(str(state["target_price"])),
        max_price=Decimal(str(state["max_price"])),
        delivery_deadline=datetime.fromisoformat(state["delivery_requirement"]),
        merchant_id=UUID(state["merchant_id"]),
        store_id=UUID(state["store_id"]),
    )
    history = list(state.get("negotiation_history", []))
    for raw_quote in state["candidate_suppliers"]:
        quote = SupplierQuote.model_validate(raw_quote)
        constraints = NegotiationConstraints(
            min_quantity=Decimal("1"),
            max_quantity=request.quantity,
            max_unit_price=request.max_price,
            allowed_supplier_ids=frozenset({str(quote.supplier_id)}),
        )
        valid, failures = services.negotiation.validate_offer(
            quote, request, constraints, round_number=1
        )
        chosen = quote
        needs_counter = quote.unit_price > request.target_price
        if (not valid and set(failures) <= {"price_limit"}) or (valid and needs_counter):
            adapter = services.supplier(quote.supplier_id)
            counter_price = services.negotiation.counter_price(quote, request)
            chosen = await adapter.counter_offer(
                quote,
                unit_price=float(counter_price),
                quantity=float(request.quantity),
                idempotency_key=f"{state['request_id']}:counter:{quote.supplier_id}",
            )
            if chosen is None:
                history.append({"supplier_id": str(quote.supplier_id), "status": "REJECTED"})
                continue
            valid, failures = services.negotiation.validate_offer(
                chosen, request, constraints, round_number=2
            )
        if valid:
            history.append(
                {
                    "supplier_id": str(chosen.supplier_id),
                    "quote_id": chosen.quote_id,
                    "unit_price": str(chosen.unit_price),
                    "status": "ACCEPTED",
                }
            )
            return {
                "selected_supplier": chosen.model_dump(mode="json"),
                "negotiated_price": float(chosen.unit_price),
                "negotiation_history": history,
                "failure_reason": "",
            }
        history.append(
            {"supplier_id": str(quote.supplier_id), "status": "INVALID", "reasons": failures}
        )
    return {"negotiation_history": history, "failure_reason": "negotiation_failed"}
