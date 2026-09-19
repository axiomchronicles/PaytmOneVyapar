from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, next_cursor
from app.api.v1.business_schemas import CursorPage, NegotiationView, StartNegotiationRequest
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import InvalidRequestError, NotFoundError
from app.domain.enums import NegotiationStatus
from app.infrastructure.db.models import (
    Approval,
    Inventory,
    Merchant,
    Negotiation,
    Product,
    Sale,
    Store,
    Supplier,
    SupplierProduct,
)
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/negotiations", tags=["negotiations"])


def _view(
    row: Negotiation, supplier: Supplier | str, approval_id: UUID | None = None
) -> NegotiationView:
    supplier_name = supplier.name if isinstance(supplier, Supplier) else str(supplier)
    return NegotiationView(
        id=row.id,
        store_id=row.store_id,
        supplier_id=row.supplier_id,
        supplier_name=supplier_name,
        correlation_id=row.correlation_id,
        workflow_request_id=row.workflow_request_id,
        proposal_id=row.proposal_id,
        approval_id=approval_id,
        sku=row.sku,
        status=row.status,
        round_count=row.round_count,
        constraints=row.constraints,
        history=row.history,
        current_quote=row.current_quote,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=CursorPage[NegotiationView])
async def list_negotiations(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    status: Annotated[NegotiationStatus | None, Query()] = None,
    supplier_id: Annotated[UUID | None, Query()] = None,
    store_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CursorPage[NegotiationView]:
    query = (
        select(Negotiation, Supplier, Approval.id)
        .join(Supplier, Supplier.id == Negotiation.supplier_id)
        .outerjoin(
            Approval,
            and_(
                Approval.merchant_id == Negotiation.merchant_id,
                Approval.proposal_id == Negotiation.proposal_id,
            ),
        )
        .where(Negotiation.merchant_id == principal.merchant_id)
    )
    if status:
        query = query.where(Negotiation.status == status)
    if supplier_id:
        query = query.where(Negotiation.supplier_id == supplier_id)
    if store_id:
        query = query.where(Negotiation.store_id == store_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Negotiation.sku.ilike(pattern), Supplier.name.ilike(pattern)))
    if created_from:
        query = query.where(Negotiation.created_at >= created_from)
    if created_to:
        query = query.where(Negotiation.created_at < created_to)
    if decoded := decode_cursor(cursor):
        created_at, row_id = decoded
        query = query.where(
            or_(
                Negotiation.created_at < created_at,
                and_(Negotiation.created_at == created_at, Negotiation.id < row_id),
            )
        )
    rows = list(
        (
            await session.execute(
                query.order_by(Negotiation.created_at.desc(), Negotiation.id.desc()).limit(
                    limit + 1
                )
            )
        ).tuples()
    )
    return CursorPage(
        items=[
            _view(row, supplier.name, approval_id) for row, supplier, approval_id in rows[:limit]
        ],
        next_cursor=next_cursor([row for row, _, _ in rows], limit),
    )


@router.get("/{negotiation_id}", response_model=NegotiationView)
async def get_negotiation(
    negotiation_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> NegotiationView:
    result = await session.execute(
        select(Negotiation, Supplier, Approval.id)
        .join(Supplier, Supplier.id == Negotiation.supplier_id)
        .outerjoin(
            Approval,
            and_(
                Approval.merchant_id == Negotiation.merchant_id,
                Approval.proposal_id == Negotiation.proposal_id,
            ),
        )
        .where(
            Negotiation.id == negotiation_id,
            Negotiation.merchant_id == principal.merchant_id,
        )
    )
    pair = result.tuples().first()
    if pair is None:
        raise NotFoundError("Negotiation not found")
    return _view(*pair)


@router.post("/start", response_model=NegotiationView, status_code=201)
async def start_negotiation(
    body: StartNegotiationRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> NegotiationView:
    """Trigger autonomous A2A procurement negotiation for an SKU with available suppliers."""
    # 1. Resolve Store
    if body.store_id:
        store = await session.scalar(
            select(Store).where(
                Store.id == body.store_id,
                Store.merchant_id == principal.merchant_id,
            )
        )
        if store is None:
            raise NotFoundError("Store not found")
    else:
        store = await session.scalar(
            select(Store).where(Store.merchant_id == principal.merchant_id).limit(1)
        )
        if store is None:
            raise NotFoundError("No store found for merchant")

    # 2. Resolve Product. A direct supplier request may be for an item not yet
    # in the buyer's own catalog, so safely copy its public catalog identity.
    product = await session.scalar(
        select(Product).where(
            Product.merchant_id == principal.merchant_id,
            func.upper(Product.sku) == body.sku.strip().upper(),
        )
    )
    if product is None and body.supplier_id is not None:
        supplier_product = (
            (
                await session.execute(
                    select(SupplierProduct, Product)
                    .join(Product, Product.id == SupplierProduct.product_id)
                    .join(Supplier, Supplier.id == SupplierProduct.supplier_id)
                    .where(
                        Supplier.id == body.supplier_id,
                        Supplier.is_active.is_(True),
                        func.upper(Product.sku) == body.sku.strip().upper(),
                    )
                    .limit(1)
                )
            )
            .tuples()
            .first()
        )
        if supplier_product is None:
            raise NotFoundError("This supplier does not list the requested item")
        _, catalog_product = supplier_product
        product = Product(
            merchant_id=principal.merchant_id,
            sku=catalog_product.sku,
            name=catalog_product.name,
            unit=catalog_product.unit,
            category=catalog_product.category,
            attributes=catalog_product.attributes or {},
        )
        session.add(product)
        await session.flush()
    if product is None:
        raise NotFoundError(f"Product with SKU '{body.sku}' not found")

    # 3. Resolve Inventory & Merchant
    inventory = await session.scalar(
        select(Inventory).where(
            Inventory.merchant_id == principal.merchant_id,
            Inventory.store_id == store.id,
            Inventory.product_id == product.id,
        )
    )
    merchant = await session.get(Merchant, principal.merchant_id)
    if merchant is None:
        raise NotFoundError("Merchant not found")

    # 4. Resolve Sales History
    sales = list(
        await session.scalars(
            select(Sale)
            .where(
                Sale.merchant_id == principal.merchant_id,
                Sale.store_id == store.id,
                Sale.product_id == product.id,
            )
            .order_by(Sale.sold_at.desc())
            .limit(90)
        )
    )
    now = datetime.now(UTC)
    if not sales:
        # Synthesize baseline sales so demand forecaster runs deterministically
        sales = [
            Sale(
                id=uuid4(),
                merchant_id=principal.merchant_id,
                store_id=store.id,
                product_id=product.id,
                quantity=Decimal("5"),
                unit_price=Decimal("100"),
                sold_at=now - timedelta(days=d),
                signals={"temperature_c": 28},
            )
            for d in range(14, 0, -1)
        ]

    # 5. Determine Quantities & Price Bounds
    qty_on_hand = float(inventory.quantity_on_hand) if inventory else 0.0
    reorder_point = float(inventory.reorder_point) if inventory else 10.0
    req_qty = float(body.quantity or max(reorder_point - qty_on_hand, 10.0))

    target_price = float(body.target_price or Decimal("440.00"))
    max_price = float(body.max_price or round(Decimal(str(target_price)) * Decimal("1.20"), 2))
    spending_limit = float(merchant.spending_limit or Decimal("50000.00"))

    req_id = f"nego_{product.sku}_{uuid4().hex[:6]}"
    state = {
        "merchant_id": str(principal.merchant_id),
        "store_id": str(store.id),
        "request_id": req_id,
        "sku": product.sku,
        "required_quantity": req_qty,
        "unit": product.unit,
        "target_price": target_price,
        "max_price": max_price,
        "spending_limit": spending_limit,
        "delivery_requirement": (now + timedelta(days=2)).isoformat(),
        "inventory_snapshot": {
            "quantity_on_hand": qty_on_hand,
            "reorder_point": reorder_point,
            "safety_stock": 0.0,
            "captured_at": now.isoformat(),
        },
        "sales_history": [
            {
                "date": s.sold_at.isoformat(),
                "sales": float(s.quantity),
                "inventory": qty_on_hand,
                "price": float(s.unit_price),
                **getattr(s, "signals", {}),
            }
            for s in reversed(sales)
        ],
        "trace_id": str(uuid4()),
        "proposal_revision": 1,
        "attempted_supplier_ids": [],
        "preferred_supplier_id": str(body.supplier_id) if body.supplier_id else None,
    }

    # 6. Execute workflow runtime through A2A negotiation
    runtime = getattr(request.app.state, "workflow_runtime", None)
    if runtime:
        await runtime.start(state)

    # 7. Fetch the recorded negotiation
    result = await session.execute(
        select(Negotiation, Supplier, Approval.id)
        .join(Supplier, Supplier.id == Negotiation.supplier_id)
        .outerjoin(
            Approval,
            and_(
                Approval.merchant_id == Negotiation.merchant_id,
                Approval.proposal_id == Negotiation.proposal_id,
            ),
        )
        .where(
            Negotiation.merchant_id == principal.merchant_id,
            Negotiation.workflow_request_id == req_id,
        )
    )
    pair = result.tuples().first()
    if pair is None and body.supplier_id is None:
        # Check by SKU
        result = await session.execute(
            select(Negotiation, Supplier, Approval.id)
            .join(Supplier, Supplier.id == Negotiation.supplier_id)
            .outerjoin(
                Approval,
                and_(
                    Approval.merchant_id == Negotiation.merchant_id,
                    Approval.proposal_id == Negotiation.proposal_id,
                ),
            )
            .where(
                Negotiation.merchant_id == principal.merchant_id,
                Negotiation.sku == product.sku,
            )
            .order_by(Negotiation.created_at.desc())
            .limit(1)
        )
        pair = result.tuples().first()

    if pair is None:
        raise InvalidRequestError(
            "The selected supplier cannot fulfil this item within the requested terms"
            if body.supplier_id
            else "Negotiation could not be completed with available suppliers"
        )

    return _view(*pair)
