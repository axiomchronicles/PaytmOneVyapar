from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.inventory_service import InventoryService
from app.application.services.recommendation_service import (
    RecommendationCandidate,
    RecommendationService,
)
from app.core.dependencies import Principal, get_current_principal
from app.infrastructure.db.repositories.inventory import InventoryRepository
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
async def recommendations(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    inventory = await InventoryService(InventoryRepository(session)).list_inventory(
        principal.merchant_id
    )
    candidates = [
        RecommendationCandidate(
            sku=item["sku"],
            shortage_ratio=max(
                0.0,
                float(item["reorder_point"] - item["quantity_on_hand"])
                / max(float(item["reorder_point"]), 1),
            ),
            sales_velocity=float(item["is_low"]),
            margin_ratio=0.5,
            supplier_availability=1.0,
        )
        for item in inventory
    ]
    return RecommendationService().rank(candidates)
