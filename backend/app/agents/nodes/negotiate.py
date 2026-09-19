from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.agents.services import WorkflowServices
from app.agents.state import PurchaseWorkflowState
from app.application.services.negotiation_service import NegotiationConstraints
from app.domain.entities import PurchaseRequest, SupplierQuote


async def negotiate(state: PurchaseWorkflowState, services: WorkflowServices) -> dict:
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
        # Round 1: Record initial quote from supplier
        history.append(
            {
                "round": 1,
                "supplier_id": str(quote.supplier_id),
                "quote_id": quote.quote_id,
                "action": "QUOTE_RECEIVED",
                "status": "INITIAL_QUOTE",
                "unit_price": str(quote.unit_price),
                "available_quantity": str(quote.available_quantity),
                "delivery_at": quote.delivery_at.isoformat(),
            }
        )
        needs_counter = quote.unit_price > request.target_price
        if (not valid and set(failures) <= {"price_limit"}) or (valid and needs_counter):
            adapter = services.supplier(quote.supplier_id)
            counter_price = services.negotiation.counter_price(quote, request)
            # Round 2: Record counter-offer from buyer agent
            history.append(
                {
                    "round": 2,
                    "supplier_id": str(quote.supplier_id),
                    "action": "COUNTER_OFFER_SENT",
                    "status": "COUNTER_OFFER",
                    "unit_price": str(counter_price),
                    "quantity": str(request.quantity),
                }
            )
            chosen = await adapter.counter_offer(
                quote,
                unit_price=float(counter_price),
                quantity=float(request.quantity),
                idempotency_key=f"{state['request_id']}:counter:{quote.supplier_id}",
            )
            if chosen is None:
                history.append(
                    {
                        "round": 2,
                        "supplier_id": str(quote.supplier_id),
                        "action": "OFFER_REJECTED",
                        "status": "REJECTED",
                    }
                )
                continue
            valid, failures = services.negotiation.validate_offer(
                chosen, request, constraints, round_number=2
            )
        if valid:
            history.append(
                {
                    "round": 2 if needs_counter else 1,
                    "supplier_id": str(chosen.supplier_id),
                    "quote_id": chosen.quote_id,
                    "action": "OFFER_ACCEPTED",
                    "unit_price": str(chosen.unit_price),
                    "status": "ACCEPTED",
                }
            )
            result = {
                "selected_supplier": chosen.model_dump(mode="json"),
                "negotiated_price": float(chosen.unit_price),
                "negotiation_history": history,
                "failure_reason": "",
            }
            adapter = services.supplier(chosen.supplier_id)
            correlation = getattr(adapter, "correlation_id_for_quote", lambda _: None)(
                chosen.quote_id
            )
            if correlation is not None:
                result["negotiation_correlation_id"] = str(correlation)
            await services.activity_recorder.record_negotiation({**state, **result})
            return result
        history.append(
            {
                "supplier_id": str(quote.supplier_id),
                "status": "INVALID",
                "reasons": list(failures),
            }
        )
    result = {"negotiation_history": history, "failure_reason": "negotiation_failed"}
    await services.activity_recorder.record_negotiation({**state, **result})
    return result
