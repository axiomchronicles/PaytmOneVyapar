from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.receipt_image import MAX_RECEIPT_IMAGE_BYTES
from app.agents.receipt_schemas import (
    ManualInventoryRequest,
    ReceiptConfirmRequest,
    ReceiptConfirmResponse,
    ReceiptReviewResponse,
)
from app.api.v1.schemas import InventoryEventRequest, InventoryItemResponse
from app.application.services.inventory_service import InventoryService
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import ConflictError
from app.infrastructure.db.repositories.inventory import InventoryRepository
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/scan-receipt", response_model=ReceiptReviewResponse)
async def scan_receipt(
    request: Request,
    image: Annotated[
        UploadFile,
        File(description="JPEG, PNG, or WebP receipt/invoice image, up to 10 MB"),
    ],
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ReceiptReviewResponse:
    try:
        content = await image.read(MAX_RECEIPT_IMAGE_BYTES + 1)
    finally:
        await image.close()
    review = await request.app.state.receipt_extraction_workflow.extract(
        filename=image.filename or "receipt",
        content_type=image.content_type or "application/octet-stream",
        content=content,
    )
    service = InventoryService(InventoryRepository(session))
    return await service.match_receipt_products(principal.merchant_id, review)


@router.post("/scan-receipt/confirm", response_model=ReceiptConfirmResponse)
async def confirm_scanned_receipt(
    body: ReceiptConfirmRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ReceiptConfirmResponse:
    service = InventoryService(InventoryRepository(session))
    try:
        result = await service.confirm_receipt(
            merchant_id=principal.merchant_id,
            user_id=principal.user_id,
            request=body,
            trace_id=getattr(request.state, "request_id", None),
        )
        await session.commit()
        return result
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "A product or receipt confirmation changed while it was being saved"
        ) from exc


@router.post("/manual", response_model=ReceiptConfirmResponse)
async def confirm_manual_inventory(
    body: ManualInventoryRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ReceiptConfirmResponse:
    service = InventoryService(InventoryRepository(session))
    try:
        result = await service.confirm_manual_inventory(
            merchant_id=principal.merchant_id,
            user_id=principal.user_id,
            request=body,
            trace_id=getattr(request.state, "request_id", None),
        )
        await session.commit()
        return result
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "A product or inventory update changed while it was being saved"
        ) from exc


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
