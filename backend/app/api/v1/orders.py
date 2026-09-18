from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, next_cursor
from app.api.v1.business_schemas import (
    CursorPage,
    OrderItemView,
    OrderView,
    TimelineEvent,
)
from app.core.dependencies import Principal, get_current_principal
from app.domain.enums import OrderStatus
from app.infrastructure.db.models import AuditLog
from app.infrastructure.db.repositories.orders import OrderRepository
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/orders", tags=["orders"])


async def serialize_order(repository: OrderRepository, order, supplier_name: str) -> OrderView:
    items = await repository.items(order.id)
    timeline = await repository.timeline(order.id, order.merchant_id)
    approval_events = []
    if order.approval_id:
        approval_events = list(
            await repository.session.scalars(
                select(AuditLog).where(
                    AuditLog.merchant_id == order.merchant_id,
                    AuditLog.resource_type == "approval",
                    AuditLog.resource_id == str(order.approval_id),
                )
            )
        )
    timeline_views = [
        TimelineEvent(
            id=event.id,
            status={
                "approval.requested": "APPROVAL_PENDING",
                "approval.granted": "APPROVED",
                "approval.modified": "MODIFIED",
                "approval.rejected": "REJECTED",
            }.get(event.action, event.action.upper().replace(".", "_")),
            occurred_at=event.created_at,
            details=event.metadata_,
        )
        for event in approval_events
    ]
    timeline_views.extend(
        TimelineEvent(
            id=event.id,
            status=event.status,
            occurred_at=event.created_at,
            details=event.details,
        )
        for event in timeline
    )
    timeline_views.sort(key=lambda event: event.occurred_at)
    return OrderView(
        id=order.id,
        proposal_id=order.proposal_id,
        approval_id=order.approval_id,
        store_id=order.store_id,
        supplier_id=order.supplier_id,
        supplier_name=supplier_name,
        status=order.status,
        total_amount=order.total_amount,
        currency=order.currency,
        supplier_reference=order.supplier_reference,
        failure_reason=order.failure_reason,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[OrderItemView.model_validate(item) for item in items],
        timeline=timeline_views,
    )


@router.get("", response_model=CursorPage[OrderView])
async def list_orders(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    status: Annotated[OrderStatus | None, Query()] = None,
    store_id: Annotated[UUID | None, Query()] = None,
    supplier_id: Annotated[UUID | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CursorPage[OrderView]:
    repository = OrderRepository(session)
    rows = await repository.list_orders(
        principal.merchant_id,
        status=status,
        store_id=store_id,
        supplier_id=supplier_id,
        created_from=created_from,
        created_to=created_to,
        search=search,
        cursor=decode_cursor(cursor),
        limit=limit,
    )
    items = [
        await serialize_order(repository, order, supplier.name) for order, supplier in rows[:limit]
    ]
    cursor_value = next_cursor([order for order, _ in rows], limit)
    return CursorPage(items=items, next_cursor=cursor_value)


@router.get("/{order_id}", response_model=OrderView)
async def get_order(
    order_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> OrderView:
    repository = OrderRepository(session)
    order = await repository.get_for_merchant(order_id, principal.merchant_id)
    supplier = await repository.supplier(order.supplier_id)
    return await serialize_order(repository, order, supplier.name)
