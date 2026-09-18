from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import AgentRunRequest
from app.core.dependencies import Principal, get_current_principal
from app.domain.enums import AgentRunStatus
from app.infrastructure.db.models import AgentRun, AgentSession
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/runs", status_code=202)
async def start_run(
    body: AgentRunRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    state = {
        "merchant_id": str(principal.merchant_id),
        "store_id": str(body.store_id),
        "request_id": body.request_id,
        "sku": body.sku,
        "required_quantity": body.required_quantity,
        "unit": body.unit,
        "target_price": body.target_price,
        "max_price": body.max_price,
        "spending_limit": body.spending_limit,
        "delivery_requirement": body.delivery_deadline.isoformat(),
        "inventory_snapshot": {
            "quantity_on_hand": body.quantity_on_hand,
            "reorder_point": body.reorder_point,
            "safety_stock": body.safety_stock,
            "captured_at": datetime.now(UTC).isoformat(),
        },
        "sales_history": body.sales_history,
        "trace_id": request.state.request_id,
        "proposal_revision": 1,
        "attempted_supplier_ids": [],
    }
    result = await request.app.state.workflow_runtime.start(state)
    thread_id = request.app.state.workflow_runtime.thread_id(
        str(principal.merchant_id), body.request_id
    )
    agent_session = await session.scalar(
        select(AgentSession).where(AgentSession.thread_id == thread_id)
    )
    if agent_session is None:
        agent_session = AgentSession(
            merchant_id=principal.merchant_id,
            store_id=body.store_id,
            thread_id=thread_id,
            channel="API",
            status="ACTIVE",
            context={"sku": body.sku},
        )
        session.add(agent_session)
        await session.flush()
    session.add(
        AgentRun(
            session_id=agent_session.id,
            request_id=body.request_id,
            trace_id=request.state.request_id,
            status=(
                AgentRunStatus.WAITING_APPROVAL
                if result.get("approval_status") == "PENDING"
                else AgentRunStatus.COMPLETED
            ),
            current_node="human_approval" if result.get("approval_status") == "PENDING" else None,
            started_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return {"request_id": body.request_id, "state": result}
