from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, next_cursor
from app.api.v1.business_schemas import (
    CursorPage,
    OffsetPage,
    SupplierProductView,
    SupplierView,
)
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import NotFoundError
from app.infrastructure.db.models import Product, Supplier, SupplierProduct
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _scope(merchant_id: UUID):
    return or_(Supplier.merchant_id == merchant_id, Supplier.merchant_id.is_(None))


async def _products(
    session: AsyncSession,
    supplier_id: UUID,
    merchant_id: UUID,
    *,
    search: str | None = None,
    available: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[SupplierProductView]:
    query = (
        select(SupplierProduct, Product)
        .join(Product, Product.id == SupplierProduct.product_id)
        .where(
            SupplierProduct.supplier_id == supplier_id,
            Product.merchant_id == merchant_id,
        )
    )
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
                SupplierProduct.supplier_sku.ilike(pattern),
            )
        )
    if available is True:
        query = query.where(SupplierProduct.available_quantity > 0)
    if available is False:
        query = query.where(SupplierProduct.available_quantity <= 0)
    rows = (
        await session.execute(
            query.order_by(Product.name, SupplierProduct.id).limit(limit).offset(offset)
        )
    ).tuples()
    return [
        SupplierProductView(
            id=item.id,
            product_id=product.id,
            supplier_sku=item.supplier_sku,
            product_name=product.name,
            merchant_sku=product.sku,
            unit=product.unit,
            available_quantity=item.available_quantity,
            unit_price=item.unit_price,
            lead_time_days=item.lead_time_days,
        )
        for item, product in rows
    ]


@router.get("", response_model=CursorPage[SupplierView])
async def list_suppliers(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    search: Annotated[str | None, Query(max_length=100)] = None,
    active: Annotated[bool | None, Query()] = True,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CursorPage[SupplierView]:
    query = select(Supplier).where(_scope(principal.merchant_id))
    if search:
        query = query.where(Supplier.name.ilike(f"%{search.strip()}%"))
    if active is not None:
        query = query.where(Supplier.is_active.is_(active))
    if created_from:
        query = query.where(Supplier.created_at >= created_from)
    if created_to:
        query = query.where(Supplier.created_at < created_to)
    if decoded := decode_cursor(cursor):
        created_at, row_id = decoded
        query = query.where(
            or_(
                Supplier.created_at < created_at,
                and_(Supplier.created_at == created_at, Supplier.id < row_id),
            )
        )
    rows = list(
        await session.scalars(
            query.order_by(Supplier.created_at.desc(), Supplier.id.desc()).limit(limit + 1)
        )
    )
    items: list[SupplierView] = []
    for supplier in rows[:limit]:
        count = await session.scalar(
            select(func.count(SupplierProduct.id))
            .join(Product, Product.id == SupplierProduct.product_id)
            .where(
                SupplierProduct.supplier_id == supplier.id,
                Product.merchant_id == principal.merchant_id,
            )
        )
        items.append(
            SupplierView(
                id=supplier.id,
                name=supplier.name,
                adapter_type=supplier.adapter_type,
                is_active=supplier.is_active,
                trust_score=supplier.trust_score,
                product_count=count or 0,
            )
        )
    return CursorPage(items=items, next_cursor=next_cursor(rows, limit))


async def _supplier(session: AsyncSession, supplier_id: UUID, merchant_id: UUID) -> Supplier:
    row = await session.scalar(
        select(Supplier).where(Supplier.id == supplier_id, _scope(merchant_id))
    )
    if row is None:
        raise NotFoundError("Supplier not found")
    return row


@router.get("/{supplier_id}", response_model=SupplierView)
async def get_supplier(
    supplier_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> SupplierView:
    supplier = await _supplier(session, supplier_id, principal.merchant_id)
    products = await _products(session, supplier.id, principal.merchant_id, limit=20)
    product_count = await session.scalar(
        select(func.count(SupplierProduct.id))
        .join(Product, Product.id == SupplierProduct.product_id)
        .where(
            SupplierProduct.supplier_id == supplier.id,
            Product.merchant_id == principal.merchant_id,
        )
    )
    return SupplierView(
        id=supplier.id,
        name=supplier.name,
        adapter_type=supplier.adapter_type,
        is_active=supplier.is_active,
        trust_score=supplier.trust_score,
        product_count=product_count or 0,
        products=products,
    )


@router.get("/{supplier_id}/products", response_model=OffsetPage[SupplierProductView])
async def supplier_products(
    supplier_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    search: Annotated[str | None, Query(max_length=100)] = None,
    available: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OffsetPage[SupplierProductView]:
    await _supplier(session, supplier_id, principal.merchant_id)
    count_query = (
        select(func.count(SupplierProduct.id))
        .join(Product, Product.id == SupplierProduct.product_id)
        .where(
            SupplierProduct.supplier_id == supplier_id,
            Product.merchant_id == principal.merchant_id,
        )
    )
    if search:
        pattern = f"%{search.strip()}%"
        count_query = count_query.where(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
                SupplierProduct.supplier_sku.ilike(pattern),
            )
        )
    if available is True:
        count_query = count_query.where(SupplierProduct.available_quantity > 0)
    if available is False:
        count_query = count_query.where(SupplierProduct.available_quantity <= 0)
    total = await session.scalar(count_query) or 0
    products = await _products(
        session,
        supplier_id,
        principal.merchant_id,
        search=search,
        available=available,
        limit=limit,
        offset=offset,
    )
    return OffsetPage(
        items=products,
        total=total,
        limit=limit,
        offset=offset,
    )
