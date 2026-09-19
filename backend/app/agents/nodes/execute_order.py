from uuid import UUID

from app.agents.services import WorkflowServices
from app.agents.state import PurchaseWorkflowState
from app.domain.entities import PurchaseProposal


async def execute_order(state: PurchaseWorkflowState, services: WorkflowServices) -> dict:
    proposal = PurchaseProposal.model_validate(state["proposal"])
    try:
        result = await services.transaction_executor.execute(
            proposal,
            approval_id=UUID(state["approval_id"]),
            approval_token=state["approval_token"],
            idempotency_key=f"{state['request_id']}:{state.get('proposal_revision', 1)}:execute",
        )
    except Exception as exc:
        attempted = [*state.get("attempted_supplier_ids", []), str(proposal.supplier_id)]
        return {
            "execution_status": "FAILED",
            "failure_reason": f"execution_failed:{type(exc).__name__}",
            "attempted_supplier_ids": attempted,
        }
    if result.status == "APPROVAL_PENDING":
        return {
            "execution_status": "WAITING_SUPPLIER_APPROVAL",
            "execution_result": result.model_dump(mode="json"),
            "failure_reason": "",
        }
    if result.status != "CONFIRMED":
        attempted = [*state.get("attempted_supplier_ids", []), str(proposal.supplier_id)]
        return {
            "execution_status": "FAILED",
            "execution_result": result.model_dump(mode="json"),
            "failure_reason": "execution_failed:supplier_rejected",
            "attempted_supplier_ids": attempted,
        }
    return {
        "execution_status": "SUCCEEDED",
        "execution_result": result.model_dump(mode="json"),
        "failure_reason": "",
    }
