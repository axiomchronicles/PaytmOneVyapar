from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, next_cursor
from app.api.v1.business_schemas import CursorPage, NegotiationView
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import NotFoundError
from app.domain.enums import NegotiationStatus
from app.infrastructure.db.models import Negotiation, Supplier
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/negotiations", tags=["negotiations"])


def _view(row: Negotiation, supplier_name: str) -> NegotiationView:
    return NegotiationView(
        id=row.id,
        store_id=row.store_id,
        supplier_id=row.supplier_id,
        supplier_name=supplier_name,
        correlation_id=row.correlation_id,
        workflow_request_id=row.workflow_request_id,
        proposal_id=row.proposal_id,
        sku=row.sku,
        status=row.status,
        round_count=row.round_count,
        constraints=row.constraints,
        history=row.history,
        current_quote=row.current_quote,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=CursorPage[NegotiationView])
async def list_negotiations(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    status: Annotated[NegotiationStatus | None, Query()] = None,
    supplier_id: Annotated[UUID | None, Query()] = None,
    store_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CursorPage[NegotiationView]:
    query = (
        select(Negotiation, Supplier)
        .join(Supplier, Supplier.id == Negotiation.supplier_id)
        .where(Negotiation.merchant_id == principal.merchant_id)
    )
    if status:
        query = query.where(Negotiation.status == status)
    if supplier_id:
        query = query.where(Negotiation.supplier_id == supplier_id)
    if store_id:
        query = query.where(Negotiation.store_id == store_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Negotiation.sku.ilike(pattern), Supplier.name.ilike(pattern)))
    if created_from:
        query = query.where(Negotiation.created_at >= created_from)
    if created_to:
        query = query.where(Negotiation.created_at < created_to)
    if decoded := decode_cursor(cursor):
        created_at, row_id = decoded
        query = query.where(
            or_(
                Negotiation.created_at < created_at,
                and_(Negotiation.created_at == created_at, Negotiation.id < row_id),
            )
        )
    rows = list(
        (
            await session.execute(
                query.order_by(Negotiation.created_at.desc(), Negotiation.id.desc()).limit(
                    limit + 1
                )
            )
        ).tuples()
    )
    return CursorPage(
        items=[_view(row, supplier.name) for row, supplier in rows[:limit]],
        next_cursor=next_cursor([row for row, _ in rows], limit),
    )


@router.get("/{negotiation_id}", response_model=NegotiationView)
async def get_negotiation(
    negotiation_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> NegotiationView:
    result = await session.execute(
        select(Negotiation, Supplier)
        .join(Supplier, Supplier.id == Negotiation.supplier_id)
        .where(
            Negotiation.id == negotiation_id,
            Negotiation.merchant_id == principal.merchant_id,
        )
    )
    pair = result.tuples().first()
    if pair is None:
        raise NotFoundError("Negotiation not found")
    return _view(*pair)
