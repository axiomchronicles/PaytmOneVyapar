from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Principal, get_current_principal
from app.core.errors import AuthorizationError
from app.infrastructure.db.repositories.orders import OrderRepository
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}")
async def get_order(
    order_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    order = await OrderRepository(session).get(order_id)
    if order.merchant_id != principal.merchant_id:
        raise AuthorizationError("Order belongs to another merchant")
    return {
        "id": order.id,
        "proposal_id": order.proposal_id,
        "supplier_id": order.supplier_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "currency": order.currency,
        "supplier_reference": order.supplier_reference,
        "failure_reason": order.failure_reason,
        "created_at": order.created_at,
    }
