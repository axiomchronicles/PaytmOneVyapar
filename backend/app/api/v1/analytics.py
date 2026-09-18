from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.business_schemas import (
    AnalyticsOverviewView,
    InventoryAnalyticsView,
    ProcurementAnalyticsView,
    SalesAnalyticsView,
)
from app.application.services.analytics_service import AnalyticsService
from app.core.dependencies import Principal, get_current_principal
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewView)
async def overview(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    store_id: Annotated[UUID | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> AnalyticsOverviewView:
    return AnalyticsOverviewView.model_validate(await AnalyticsService(session).overview(
        principal.merchant_id,
        store_id=store_id,
        created_from=created_from,
        created_to=created_to,
    ))


@router.get("/sales", response_model=SalesAnalyticsView)
async def sales(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    store_id: Annotated[UUID | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    group_by: Annotated[str, Query(pattern="^(day|week|month)$")] = "day",
) -> SalesAnalyticsView:
    return SalesAnalyticsView.model_validate(await AnalyticsService(session).sales(
        principal.merchant_id,
        store_id=store_id,
        created_from=created_from,
        created_to=created_to,
        group_by=group_by,
    ))


@router.get("/inventory", response_model=InventoryAnalyticsView)
async def inventory(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    store_id: Annotated[UUID | None, Query()] = None,
) -> InventoryAnalyticsView:
    return InventoryAnalyticsView.model_validate(
        await AnalyticsService(session).inventory(principal.merchant_id, store_id=store_id)
    )


@router.get("/procurement", response_model=ProcurementAnalyticsView)
async def procurement(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    store_id: Annotated[UUID | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> ProcurementAnalyticsView:
    return ProcurementAnalyticsView.model_validate(await AnalyticsService(session).procurement(
        principal.merchant_id,
        store_id=store_id,
        created_from=created_from,
        created_to=created_to,
    ))
