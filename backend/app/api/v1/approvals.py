from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, next_cursor
from app.api.v1.business_schemas import ApprovalView, CursorPage
from app.api.v1.schemas import (
    ApprovalDecisionRequest,
    ApprovalModificationRequest,
    ApprovalRejectRequest,
)
from app.application.services.approval_service import ApprovalService
from app.core.config import Settings, get_settings
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import ConflictError
from app.core.security import canonical_order_hash
from app.domain.enums import AgentRunStatus, ApprovalStatus
from app.infrastructure.db.models import AgentRun, IdempotencyKey
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
        "workflow_request_id": row.workflow_request_id,
        "order_hash": row.order_hash,
        "proposal": row.proposal_payload,
        "status": row.status,
        "revision": row.revision,
        "expires_at": row.expires_at,
        "decided_at": row.decided_at,
        "created_at": row.created_at,
    }


def _pending_and_current(row) -> bool:
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return row.status == ApprovalStatus.PENDING and expires_at > datetime.now(UTC)


async def _idempotency_begin(
    session: AsyncSession, *, scope: str, key: str, request_data: dict
) -> tuple[IdempotencyKey, dict | None]:
    request_hash = canonical_order_hash(request_data)
    row = await session.scalar(
        select(IdempotencyKey)
        .where(IdempotencyKey.scope == scope, IdempotencyKey.key == key)
        .with_for_update()
    )
    if row is not None:
        if row.request_hash != request_hash:
            raise ConflictError("Idempotency key was reused with a different request")
        if row.status == "COMPLETED" and row.response is not None:
            return row, row.response
        raise ConflictError("The approval action is already being processed")
    row = IdempotencyKey(scope=scope, key=key, request_hash=request_hash)
    session.add(row)
    return row, None


def _idempotency_complete(row: IdempotencyKey, response: dict) -> dict:
    encoded = jsonable_encoder(response)
    row.status = "COMPLETED"
    row.response = encoded
    return encoded


@router.get("", response_model=CursorPage[ApprovalView])
async def list_approvals(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    status: Annotated[ApprovalStatus | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CursorPage[ApprovalView]:
    repository = ApprovalRepository(session)
    rows = await repository.list(
        principal.merchant_id,
        status=status,
        created_from=created_from,
        created_to=created_to,
        cursor=decode_cursor(cursor),
        limit=limit,
    )
    items = []
    service = ApprovalService(
        repository,
        secret=settings.auth_approval_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.auth_approval_token_minutes,
    )
    for row in rows[:limit]:
        data = serialize(row)
        if _pending_and_current(row):
            data["action_token"] = service.token_for(row, merchant_id=principal.merchant_id)
        items.append(ApprovalView.model_validate(data))
    return CursorPage(items=items, next_cursor=next_cursor(rows, limit))


@router.get("/{approval_id}", response_model=ApprovalView)
async def get_approval(
    approval_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApprovalView:
    repository = ApprovalRepository(session)
    row = await repository.get(approval_id, merchant_id=principal.merchant_id)
    data = serialize(row)
    if _pending_and_current(row):
        data["action_token"] = ApprovalService(
            repository,
            secret=settings.auth_approval_secret.get_secret_value(),
            algorithm=settings.auth_jwt_algorithm,
            ttl_minutes=settings.auth_approval_token_minutes,
        ).token_for(row, merchant_id=principal.merchant_id)
    return ApprovalView.model_validate(data)


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    idempotency, cached = await _idempotency_begin(
        session,
        scope=f"approval:{principal.merchant_id}:{approval_id}:approve",
        key=body.idempotency_key,
        request_data=body.model_dump(mode="json"),
    )
    if cached is not None:
        return cached
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
        response = _idempotency_complete(
            idempotency, {"approval_id": approval_id, "workflow": state}
        )
        await session.commit()
        return response
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
    response = _idempotency_complete(idempotency, serialize(row))
    await session.commit()
    return response


@router.post("/{approval_id}/modify", status_code=201)
async def modify(
    approval_id: UUID,
    body: ApprovalModificationRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    idempotency, cached = await _idempotency_begin(
        session,
        scope=f"approval:{principal.merchant_id}:{approval_id}:modify",
        key=body.idempotency_key,
        request_data=body.model_dump(mode="json"),
    )
    if cached is not None:
        return cached
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
    response = _idempotency_complete(
        idempotency, {"superseded_approval_id": approval_id, "workflow": state}
    )
    await session.commit()
    return response


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: UUID,
    body: ApprovalRejectRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    idempotency, cached = await _idempotency_begin(
        session,
        scope=f"approval:{principal.merchant_id}:{approval_id}:reject",
        key=body.idempotency_key,
        request_data=body.model_dump(mode="json"),
    )
    if cached is not None:
        return cached
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
        response = _idempotency_complete(
            idempotency, {"approval_id": approval_id, "workflow": state}
        )
        await session.commit()
        return response
    service = ApprovalService(
        ApprovalRepository(session),
        secret=settings.auth_approval_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.auth_approval_token_minutes,
    )
    row = await service.reject(
        approval_id, merchant_id=principal.merchant_id, user_id=principal.user_id
    )
    response = _idempotency_complete(idempotency, serialize(row))
    await session.commit()
    return response
