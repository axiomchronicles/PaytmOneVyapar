from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, next_cursor
from app.api.v1.business_schemas import ActivityView, CursorPage, InventoryHistoryView
from app.core.dependencies import Principal, get_current_principal
from app.infrastructure.db.models import AuditLog, InventoryEvent
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/activity", response_model=CursorPage[ActivityView])
async def activity_history(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    resource_type: Annotated[str | None, Query(max_length=100)] = None,
    action: Annotated[str | None, Query(max_length=100)] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CursorPage[ActivityView]:
    query = select(AuditLog).where(AuditLog.merchant_id == principal.merchant_id)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if action:
        query = query.where(AuditLog.action == action)
    if created_from:
        query = query.where(AuditLog.created_at >= created_from)
    if created_to:
        query = query.where(AuditLog.created_at < created_to)
    if decoded := decode_cursor(cursor):
        created_at, row_id = decoded
        query = query.where(
            or_(
                AuditLog.created_at < created_at,
                and_(AuditLog.created_at == created_at, AuditLog.id < row_id),
            )
        )
    rows = list(
        await session.scalars(
            query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit + 1)
        )
    )
    return CursorPage(
        items=[
            ActivityView(
                id=row.id,
                action=row.action,
                actor_type=row.actor_type,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                trace_id=row.trace_id,
                metadata=row.metadata_,
                occurred_at=row.created_at,
            )
            for row in rows[:limit]
        ],
        next_cursor=next_cursor(rows, limit),
    )


@router.get("/inventory", response_model=CursorPage[InventoryHistoryView])
async def inventory_history(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    store_id: Annotated[UUID | None, Query()] = None,
    product_id: Annotated[UUID | None, Query()] = None,
    event_type: Annotated[str | None, Query(max_length=50)] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CursorPage[InventoryHistoryView]:
    query = select(InventoryEvent).where(InventoryEvent.merchant_id == principal.merchant_id)
    if store_id:
        query = query.where(InventoryEvent.store_id == store_id)
    if product_id:
        query = query.where(InventoryEvent.product_id == product_id)
    if event_type:
        query = query.where(InventoryEvent.event_type == event_type)
    if created_from:
        query = query.where(InventoryEvent.created_at >= created_from)
    if created_to:
        query = query.where(InventoryEvent.created_at < created_to)
    if decoded := decode_cursor(cursor):
        created_at, row_id = decoded
        query = query.where(
            or_(
                InventoryEvent.created_at < created_at,
                and_(InventoryEvent.created_at == created_at, InventoryEvent.id < row_id),
            )
        )
    rows = list(
        await session.scalars(
            query.order_by(InventoryEvent.created_at.desc(), InventoryEvent.id.desc()).limit(
                limit + 1
            )
        )
    )
    return CursorPage(
        items=[
            InventoryHistoryView(
                id=row.id,
                store_id=row.store_id,
                product_id=row.product_id,
                event_type=row.event_type,
                quantity_delta=row.quantity_delta,
                quantity_after=row.quantity_after,
                source=row.source,
                occurred_at=row.created_at,
            )
            for row in rows[:limit]
        ],
        next_cursor=next_cursor(rows, limit),
    )
