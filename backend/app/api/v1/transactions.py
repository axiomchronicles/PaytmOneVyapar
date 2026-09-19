from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.business_schemas import OffsetPage, SettlementDetailView, TransactionView
from app.core.dependencies import Principal, get_current_principal
from app.infrastructure.db.models import Settlement, Transaction
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=OffsetPage[TransactionView])
async def list_transactions(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OffsetPage[TransactionView]:
    query = select(Transaction).where(Transaction.merchant_id == principal.merchant_id)
    count_query = select(func.count(Transaction.id)).where(Transaction.merchant_id == principal.merchant_id)

    if status:
        query = query.where(Transaction.status == status)
        count_query = count_query.where(Transaction.status == status)

    total = (await session.scalar(count_query)) or 0
    items = list(
        await session.scalars(
            query.order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )

    return OffsetPage[TransactionView](
        items=[TransactionView.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/settlements/history", response_model=OffsetPage[SettlementDetailView])
async def list_settlements(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OffsetPage[SettlementDetailView]:
    query = select(Settlement).where(Settlement.merchant_id == principal.merchant_id)
    count_query = select(func.count(Settlement.id)).where(Settlement.merchant_id == principal.merchant_id)

    total = (await session.scalar(count_query)) or 0
    items = list(
        await session.scalars(
            query.order_by(Settlement.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )

    return OffsetPage[SettlementDetailView](
        items=[SettlementDetailView.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
