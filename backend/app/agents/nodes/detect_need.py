from app.agents.state import PurchaseWorkflowState


def detect_need(state: PurchaseWorkflowState) -> dict:
    snapshot = state["inventory_snapshot"]
    if float(snapshot["quantity_on_hand"]) > float(snapshot["reorder_point"]):
        return {"failure_reason": "inventory_above_reorder_point"}
    return {"failure_reason": "", "proposal_revision": state.get("proposal_revision", 1)}
