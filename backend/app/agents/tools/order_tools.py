from app.domain.contracts import TransactionExecutor
from app.domain.entities import PurchaseProposal


async def execute_validated_order(
    executor: TransactionExecutor,
    proposal: PurchaseProposal,
    *,
    approval_id,
    approval_token: str,
    idempotency_key: str,
):
    return await executor.execute(
        proposal,
        approval_id=approval_id,
        approval_token=approval_token,
        idempotency_key=idempotency_key,
    )
