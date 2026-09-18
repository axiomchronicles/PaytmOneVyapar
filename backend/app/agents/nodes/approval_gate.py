from langgraph.types import interrupt

from app.agents.state import PurchaseWorkflowState


def approval_gate(state: PurchaseWorkflowState) -> dict:
    decision = interrupt(
        {
            "approval_id": state["approval_id"],
            "proposal": state["proposal"],
            "order_hash": state["order_hash"],
            "approval_token": state["approval_token"],
            "allowed_actions": ["APPROVE", "MODIFY", "REJECT"],
        }
    )
    action = decision["action"]
    if action == "MODIFY":
        updates = {
            "approval_status": "MODIFIED",
            "proposal_revision": state.get("proposal_revision", 1) + 1,
            "attempted_supplier_ids": [],
            "merchant_quantity_override": True,
            "failure_reason": "",
        }
        if decision.get("quantity") is not None:
            updates["required_quantity"] = float(decision["quantity"])
        if decision.get("max_unit_price") is not None:
            updates["max_price"] = float(decision["max_unit_price"])
        return updates
    if action == "REJECT":
        return {"approval_status": "REJECTED", "failure_reason": "merchant_rejected"}
    return {"approval_status": "APPROVED"}
