from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import (
    ApprovalDecisionRequest,
    ApprovalModificationRequest,
    ApprovalRejectRequest,
)
from app.application.services.approval_service import ApprovalService
from app.core.config import Settings, get_settings
from app.core.dependencies import Principal, get_current_principal
from app.domain.enums import AgentRunStatus, ApprovalStatus
from app.infrastructure.db.models import AgentRun
from app.infrastructure.db.repositories.approvals import ApprovalRepository
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/approvals", tags=["approvals"])


async def update_agent_run(session: AsyncSession, request_id: str, state: dict) -> None:
    run = await session.scalar(select(AgentRun).where(AgentRun.request_id == request_id))
    if run is None:
        return
    if state.get("approval_status") == ApprovalStatus.PENDING:
        run.status = AgentRunStatus.WAITING_APPROVAL
        run.current_node = "human_approval"
        return
    run.status = (
        AgentRunStatus.COMPLETED
        if state.get("execution_status") == "VERIFIED"
        or state.get("approval_status") == ApprovalStatus.REJECTED
        else AgentRunStatus.FAILED
    )
    run.current_node = None
    run.finished_at = datetime.now(UTC)


def serialize(row) -> dict:
    return {
        "id": row.id,
        "proposal_id": row.proposal_id,
        "merchant_id": row.merchant_id,
        "order_hash": row.order_hash,
        "proposal": row.proposal_payload,
        "status": row.status,
        "expires_at": row.expires_at,
        "created_at": row.created_at,
    }


@router.get("/{approval_id}")
async def get_approval(
    approval_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    row = await ApprovalRepository(session).get(approval_id)
    if row.merchant_id != principal.merchant_id:
        from app.core.errors import AuthorizationError

        raise AuthorizationError("Approval belongs to another merchant")
    return serialize(row)


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    if body.request_id:
        state = await request.app.state.workflow_runtime.resume(
            merchant_id=principal.merchant_id,
            request_id=body.request_id,
            action=ApprovalStatus.APPROVED,
            approval_token=body.approval_token,
            user_id=principal.user_id,
            expected_approval_id=approval_id,
        )
        await update_agent_run(session, body.request_id, state)
        await session.commit()
        return {"approval_id": approval_id, "workflow": state}
    service = ApprovalService(
        ApprovalRepository(session),
        secret=settings.auth_approval_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.auth_approval_token_minutes,
    )
    row = await service.approve(
        approval_id,
        merchant_id=principal.merchant_id,
        user_id=principal.user_id,
        token=body.approval_token,
    )
    await session.commit()
    return serialize(row)


@router.post("/{approval_id}/modify", status_code=201)
async def modify(
    approval_id: UUID,
    body: ApprovalModificationRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    state = await request.app.state.workflow_runtime.resume(
        merchant_id=principal.merchant_id,
        request_id=body.request_id,
        action=ApprovalStatus.MODIFIED,
        approval_token=body.approval_token,
        quantity=float(body.quantity) if body.quantity else None,
        max_unit_price=float(body.max_unit_price) if body.max_unit_price else None,
        user_id=principal.user_id,
        expected_approval_id=approval_id,
    )
    await update_agent_run(session, body.request_id, state)
    await session.commit()
    return {"superseded_approval_id": approval_id, "workflow": state}


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: UUID,
    body: ApprovalRejectRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    if body.request_id:
        snapshot = await request.app.state.workflow_runtime.state(
            principal.merchant_id, body.request_id
        )
        state = await request.app.state.workflow_runtime.resume(
            merchant_id=principal.merchant_id,
            request_id=body.request_id,
            action=ApprovalStatus.REJECTED,
            approval_token=snapshot["approval_token"],
            user_id=principal.user_id,
            expected_approval_id=approval_id,
        )
        await update_agent_run(session, body.request_id, state)
        await session.commit()
        return {"approval_id": approval_id, "workflow": state}
    service = ApprovalService(
        ApprovalRepository(session),
        secret=settings.auth_approval_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.auth_approval_token_minutes,
    )
    row = await service.reject(
        approval_id, merchant_id=principal.merchant_id, user_id=principal.user_id
    )
    await session.commit()
    return serialize(row)
