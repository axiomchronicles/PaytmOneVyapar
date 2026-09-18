from app.agents.state import PurchaseWorkflowState


def verify_result(state: PurchaseWorkflowState) -> dict:
    result = state.get("execution_result")
    if state.get("execution_status") != "SUCCEEDED" or not result:
        return {"failure_reason": state.get("failure_reason", "order_not_confirmed")}
    if result.get("status") != "CONFIRMED" or not result.get("supplier_confirmation"):
        return {"execution_status": "FAILED", "failure_reason": "supplier_confirmation_missing"}
    return {"execution_status": "VERIFIED", "failure_reason": ""}
