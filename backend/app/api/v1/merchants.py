from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.merchant_service import MerchantService
from app.core.dependencies import Principal, get_current_principal
from app.infrastructure.db.repositories.merchants import MerchantRepository
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("/me")
async def me(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await MerchantService(MerchantRepository(session)).profile(principal.merchant_id)
