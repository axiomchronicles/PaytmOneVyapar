from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, next_cursor
from app.api.v1.business_schemas import CursorPage, NotificationView
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import NotFoundError
from app.core.security import utc_now
from app.domain.enums import NotificationType
from app.infrastructure.db.models import Notification
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _view(row: Notification) -> NotificationView:
    return NotificationView(
        id=row.id,
        notification_type=row.notification_type,
        title=row.title,
        body=row.body,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        payload=row.payload,
        is_read=row.is_read,
        read_at=row.read_at,
        created_at=row.created_at,
    )


@router.get("", response_model=CursorPage[NotificationView])
async def list_notifications(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    unread_only: Annotated[bool, Query()] = False,
    notification_type: Annotated[NotificationType | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CursorPage[NotificationView]:
    query = select(Notification).where(
        Notification.merchant_id == principal.merchant_id,
        or_(Notification.user_id.is_(None), Notification.user_id == principal.user_id),
    )
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    if notification_type:
        query = query.where(Notification.notification_type == notification_type)
    if decoded := decode_cursor(cursor):
        created_at, row_id = decoded
        query = query.where(
            or_(
                Notification.created_at < created_at,
                and_(Notification.created_at == created_at, Notification.id < row_id),
            )
        )
    rows = list(
        await session.scalars(
            query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit + 1)
        )
    )
    return CursorPage(
        items=[_view(row) for row in rows[:limit]],
        next_cursor=next_cursor(rows, limit),
    )


@router.get("/{notification_id}", response_model=NotificationView)
async def notification_detail(
    notification_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> NotificationView:
    row = await session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.merchant_id == principal.merchant_id,
            or_(Notification.user_id.is_(None), Notification.user_id == principal.user_id),
        )
    )
    if row is None:
        raise NotFoundError("Notification not found")
    return _view(row)


@router.patch("/{notification_id}/read", response_model=NotificationView)
async def mark_read(
    notification_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> NotificationView:
    row = await session.scalar(
        select(Notification)
        .where(
            Notification.id == notification_id,
            Notification.merchant_id == principal.merchant_id,
            or_(Notification.user_id.is_(None), Notification.user_id == principal.user_id),
        )
        .with_for_update()
    )
    if row is None:
        raise NotFoundError("Notification not found")
    row.is_read = True
    row.read_at = utc_now()
    await session.commit()
    return _view(row)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> None:
    await session.execute(
        update(Notification)
        .where(
            Notification.merchant_id == principal.merchant_id,
            or_(Notification.user_id.is_(None), Notification.user_id == principal.user_id),
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=utc_now())
    )
    await session.commit()
