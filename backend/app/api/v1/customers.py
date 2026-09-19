from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.business_schemas import CustomerView, OffsetPage
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import NotFoundError
from app.infrastructure.db.models import Customer
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=OffsetPage[CustomerView])
async def list_customers(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    search: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OffsetPage[CustomerView]:
    query = select(Customer).where(Customer.merchant_id == principal.merchant_id)
    count_query = select(func.count(Customer.id)).where(Customer.merchant_id == principal.merchant_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        flt = or_(Customer.name.ilike(term), Customer.phone_number.ilike(term))
        query = query.where(flt)
        count_query = count_query.where(flt)

    total = (await session.scalar(count_query)) or 0
    items = list(
        await session.scalars(
            query.order_by(Customer.total_spent.desc(), Customer.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )

    return OffsetPage[CustomerView](
        items=[CustomerView.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{customer_id}", response_model=CustomerView)
async def get_customer(
    customer_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> CustomerView:
    customer = await session.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.merchant_id == principal.merchant_id,
        )
    )
    if not customer:
        raise NotFoundError("Customer not found")
    return CustomerView.model_validate(customer)
