from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.business_schemas import CampaignRequest, CampaignResponse, PaymentQRView
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


@router.get("/qr", response_model=PaymentQRView)
async def payment_qr(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    store_id: Annotated[UUID | None, Query()] = None,
) -> PaymentQRView:
    return PaymentQRView.model_validate(
        await MerchantService(MerchantRepository(session)).get_payment_qr(
            principal.merchant_id,
            store_id=store_id,
        )
    )


@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(
    payload: CampaignRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> CampaignResponse:
    return CampaignResponse.model_validate(
        await MerchantService(MerchantRepository(session)).create_campaign(
            principal.merchant_id,
            title=payload.title,
            discount_pct=payload.discount_pct,
            target_audience=payload.target_audience,
        )
    )
