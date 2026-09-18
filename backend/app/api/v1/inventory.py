from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import InventoryEventRequest, InventoryItemResponse
from app.application.services.inventory_service import InventoryService
from app.core.dependencies import Principal, get_current_principal
from app.infrastructure.db.repositories.inventory import InventoryRepository
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryItemResponse])
async def inventory(
    store_id: UUID | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    service = InventoryService(InventoryRepository(session))
    return await service.list_inventory(principal.merchant_id, store_id)


@router.post("/events", status_code=201)
async def inventory_event(
    body: InventoryEventRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    service = InventoryService(InventoryRepository(session))
    result = await service.record_event(merchant_id=principal.merchant_id, **body.model_dump())
    await session.commit()
    return result
