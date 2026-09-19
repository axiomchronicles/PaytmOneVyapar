from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, next_cursor
from app.api.v1.business_schemas import (
    CursorPage,
    NearbyMerchantView,
    NearbySupplierView,
    OffsetPage,
    OrderView,
    SupplierCatalogUpsertRequest,
    SupplierOrderDecisionRequest,
    SupplierProductView,
    SupplierView,
)
from app.api.v1.orders import serialize_order
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import AuthorizationError, ConflictError, NotFoundError
from app.domain.enums import NotificationType, OrderStatus, TransactionStatus
from app.domain.events import EventType
from app.infrastructure.db.models import (
    Merchant,
    Notification,
    Order,
    OrderEvent,
    OutboxEvent,
    Product,
    Store,
    Supplier,
    SupplierProduct,
    Transaction,
)
from app.infrastructure.db.repositories.orders import OrderRepository
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _scope(merchant_id: UUID):
    return or_(Supplier.merchant_id == merchant_id, Supplier.merchant_id.is_(None))


async def _products(
    session: AsyncSession,
    supplier_id: UUID,
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


async def _supplier(session: AsyncSession, supplier_id: UUID, merchant_id: UUID) -> Supplier:
    row = await session.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            or_(_scope(merchant_id), Supplier.is_active.is_(True)),
        )
    )
    if row is None:
        raise NotFoundError("Supplier not found")
    return row


async def _owned_supplier(session: AsyncSession, principal: Principal) -> Supplier:
    if principal.role.lower() != "supplier":
        raise AuthorizationError("A supplier account is required for this action")
    supplier = await session.scalar(
        select(Supplier).where(Supplier.merchant_id == principal.merchant_id).with_for_update()
    )
    if supplier is None:
        raise NotFoundError("Supplier profile not found for this account")
    return supplier


# --- Discovery Endpoints (Registered before /{supplier_id} to avoid path collisions) ---


@router.get("/discovery/nearby", response_model=OffsetPage[NearbySupplierView])
async def discover_nearby_suppliers(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    search: Annotated[str | None, Query(max_length=100)] = None,
    city: Annotated[str | None, Query(max_length=100)] = None,
    state: Annotated[str | None, Query(max_length=100)] = None,
    pincode: Annotated[str | None, Query(max_length=10)] = None,
    category: Annotated[str | None, Query(max_length=100)] = None,
    radius_km: Annotated[float | None, Query(ge=0, le=500)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OffsetPage[NearbySupplierView]:
    """Return every active supplier; distance is presentation-only for the demo."""

    query = select(Supplier).where(Supplier.is_active.is_(True))

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Supplier.name.ilike(term),
                Supplier.city.ilike(term),
                Supplier.category.ilike(term),
            )
        )
    if category and category.strip():
        query = query.where(Supplier.category.ilike(f"%{category.strip()}%"))

    suppliers = list(
        await session.scalars(query.order_by(Supplier.trust_score.desc(), Supplier.name))
    )

    items: list[NearbySupplierView] = []
    for s in suppliers:
        # The hackathon UI needs a familiar "nearby" signal.  This is a stable
        # display value only; it never hides an active supplier.
        dist = round(1.2 + ((s.id.int % 38) * 0.1), 1)

        p_count = (
            await session.scalar(
                select(func.count(SupplierProduct.id)).where(SupplierProduct.supplier_id == s.id)
            )
        ) or 0

        items.append(
            NearbySupplierView(
                id=s.id,
                name=s.name,
                city=s.city,
                state=s.state,
                pincode=s.pincode,
                locality=s.city,
                distance_km=dist,
                trust_score=s.trust_score or Decimal("0.95"),
                product_count=p_count,
                phone_number=s.phone_number,
                category=s.category,
            )
        )

    total = len(items)
    paged_items = items[offset : offset + limit]
    return OffsetPage[NearbySupplierView](
        items=paged_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/merchants", response_model=OffsetPage[NearbyMerchantView], include_in_schema=False)
@router.get("/discovery/merchants", response_model=OffsetPage[NearbyMerchantView])
async def discover_nearby_merchants(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    search: Annotated[str | None, Query(max_length=100)] = None,
    city: Annotated[str | None, Query(max_length=100)] = None,
    state: Annotated[str | None, Query(max_length=100)] = None,
    pincode: Annotated[str | None, Query(max_length=10)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OffsetPage[NearbyMerchantView]:
    """Return all other merchants; distance is presentation-only for the demo."""

    # Find merchants with their primary store
    merchants_query = select(Merchant).where(Merchant.id != principal.merchant_id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        merchants_query = merchants_query.where(
            or_(
                Merchant.name.ilike(term),
            )
        )

    merchants = list(await session.scalars(merchants_query.order_by(Merchant.name)))

    items: list[NearbyMerchantView] = []
    for m in merchants:
        # Get merchant store
        store = await session.scalar(select(Store).where(Store.merchant_id == m.id).limit(1))
        m_city = store.city if store else None
        m_state = store.state if store else None
        m_pincode = store.pincode if store else None

        p_count = (
            await session.scalar(select(func.count(Product.id)).where(Product.merchant_id == m.id))
        ) or 0

        dist = round(0.8 + ((m.id.int % 40) * 0.1), 1)

        items.append(
            NearbyMerchantView(
                id=m.id,
                name=m.name,
                city=m_city,
                state=m_state,
                pincode=m_pincode,
                locality=m_city,
                distance_km=dist,
                product_count=p_count,
                # Phone numbers belong to the merchant/business, not its user login.
                phone_number=m.phone_number,
                business_type=getattr(m, "business_type", "retail") or "retail",
            )
        )

    total = len(items)
    paged_items = items[offset : offset + limit]
    return OffsetPage[NearbyMerchantView](
        items=paged_items,
        total=total,
        limit=limit,
        offset=offset,
    )


# --- Authenticated Supplier Endpoints ---


@router.get("/me", response_model=SupplierView)
async def get_my_supplier_profile(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> SupplierView:
    supplier = await session.scalar(
        select(Supplier).where(Supplier.merchant_id == principal.merchant_id)
    )
    if not supplier:
        raise NotFoundError("Supplier profile not found for this account")

    product_count = (
        await session.scalar(
            select(func.count(SupplierProduct.id)).where(SupplierProduct.supplier_id == supplier.id)
        )
    ) or 0
    products = await _products(session, supplier.id, limit=20)
    return SupplierView(
        id=supplier.id,
        name=supplier.name,
        adapter_type=supplier.adapter_type,
        is_active=supplier.is_active,
        trust_score=supplier.trust_score,
        product_count=product_count,
        phone_number=supplier.phone_number,
        gstin=supplier.gstin,
        city=supplier.city,
        state=supplier.state,
        pincode=supplier.pincode,
        category=supplier.category,
        products=products,
    )


@router.post("/me/products", response_model=SupplierProductView, status_code=201)
async def upsert_supplier_product(
    body: SupplierCatalogUpsertRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> SupplierProductView:
    """Create or replenish a supplier-managed catalog item."""
    supplier = await _owned_supplier(session, principal)
    sku = body.sku.strip().upper()
    product = await session.scalar(
        select(Product)
        .where(Product.merchant_id == principal.merchant_id, Product.sku == sku)
        .with_for_update()
    )
    if product is None:
        product = Product(
            merchant_id=principal.merchant_id,
            sku=sku,
            name=body.name.strip(),
            unit=body.unit.strip(),
            category=body.category.strip() if body.category else None,
        )
        session.add(product)
        await session.flush()
    else:
        product.name = body.name.strip()
        product.unit = body.unit.strip()
        product.category = body.category.strip() if body.category else product.category

    catalog_item = await session.scalar(
        select(SupplierProduct)
        .where(SupplierProduct.supplier_id == supplier.id, SupplierProduct.product_id == product.id)
        .with_for_update()
    )
    if catalog_item is None:
        catalog_item = SupplierProduct(
            supplier_id=supplier.id,
            product_id=product.id,
            supplier_sku=(body.supplier_sku or sku).strip().upper(),
            available_quantity=body.available_quantity,
            unit_price=body.unit_price,
            lead_time_days=body.lead_time_days,
        )
        session.add(catalog_item)
    else:
        catalog_item.supplier_sku = (body.supplier_sku or sku).strip().upper()
        catalog_item.available_quantity = body.available_quantity
        catalog_item.unit_price = body.unit_price
        catalog_item.lead_time_days = body.lead_time_days
    await session.flush()
    await session.commit()
    return SupplierProductView(
        id=catalog_item.id,
        product_id=product.id,
        supplier_sku=catalog_item.supplier_sku,
        product_name=product.name,
        merchant_sku=product.sku,
        unit=product.unit,
        available_quantity=catalog_item.available_quantity,
        unit_price=catalog_item.unit_price,
        lead_time_days=catalog_item.lead_time_days,
    )


@router.get("/me/orders", response_model=OffsetPage[OrderView])
async def get_supplier_orders(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OffsetPage[OrderView]:
    supplier = await session.scalar(
        select(Supplier).where(Supplier.merchant_id == principal.merchant_id)
    )
    if not supplier:
        return OffsetPage[OrderView](items=[], total=0, limit=limit, offset=offset)

    query = select(Order).where(Order.supplier_id == supplier.id)
    count_query = select(func.count(Order.id)).where(Order.supplier_id == supplier.id)
    if status:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)

    total = (await session.scalar(count_query)) or 0
    orders = list(
        await session.scalars(query.order_by(Order.created_at.desc()).limit(limit).offset(offset))
    )
    repository = OrderRepository(session)
    items = [await serialize_order(repository, order, supplier.name) for order in orders]
    return OffsetPage[OrderView](items=items, total=total, limit=limit, offset=offset)


@router.post("/me/orders/{order_id}/decision", response_model=OrderView)
async def decide_supplier_order(
    order_id: UUID,
    body: SupplierOrderDecisionRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> OrderView:
    """Supplier human gate: reserve catalog stock, then settle or reject an order."""
    supplier = await _owned_supplier(session, principal)
    order = await session.scalar(
        select(Order)
        .where(Order.id == order_id, Order.supplier_id == supplier.id)
        .with_for_update()
    )
    if order is None:
        raise NotFoundError("Incoming order not found")
    if order.status != OrderStatus.APPROVAL_PENDING:
        if (body.approved and order.status == OrderStatus.CONFIRMED) or (
            not body.approved and order.status == OrderStatus.CANCELLED
        ):
            return await serialize_order(OrderRepository(session), order, supplier.name)
        raise ConflictError(f"Order is already {order.status}")

    items = await OrderRepository(session).items(order.id)
    if body.approved:
        for order_item in items:
            catalog_item = await session.scalar(
                select(SupplierProduct)
                .join(Product, Product.id == SupplierProduct.product_id)
                .where(
                    SupplierProduct.supplier_id == supplier.id,
                    func.upper(Product.sku) == order_item.sku.upper(),
                )
                .with_for_update()
            )
            if catalog_item is None or catalog_item.available_quantity < order_item.quantity:
                raise ConflictError(f"Insufficient catalog stock for {order_item.sku}")
            catalog_item.available_quantity -= order_item.quantity
        order.status = OrderStatus.CONFIRMED
        order.supplier_reference = order.supplier_reference or f"PO-{str(order.id)[:8].upper()}"
        transaction_status = TransactionStatus.SUCCEEDED
        event_type = EventType.ORDER_EXECUTED
        title = "Supplier confirmed your order"
        message = "The supplier approved the order. Settlement has started."
    else:
        order.status = OrderStatus.CANCELLED
        order.failure_reason = "supplier_rejected"
        transaction_status = TransactionStatus.FAILED
        event_type = EventType.ORDER_FAILED
        title = "Supplier could not fulfil your order"
        message = "The supplier declined the order before settlement."

    transaction = await session.scalar(select(Transaction).where(Transaction.order_id == order.id))
    if transaction is not None:
        transaction.status = transaction_status
        transaction.provider_reference = order.supplier_reference if body.approved else None
        transaction.error = None if body.approved else {"reason": "supplier_rejected"}
    session.add(
        OrderEvent(
            merchant_id=order.merchant_id,
            order_id=order.id,
            status=order.status,
            details={"supplier_decision": "APPROVED" if body.approved else "REJECTED"},
        )
    )
    notification = Notification(
        merchant_id=order.merchant_id,
        notification_type=NotificationType.ORDER_UPDATE,
        title=title,
        body=message,
        entity_type="order",
        entity_id=order.id,
        payload={"status": order.status},
    )
    session.add(notification)
    await session.flush()
    session.add(
        OutboxEvent(
            merchant_id=order.merchant_id,
            aggregate_type="order",
            aggregate_id=order.id,
            event_type=event_type,
            payload={"order_id": str(order.id), "status": order.status},
        )
    )
    session.add(
        OutboxEvent(
            merchant_id=order.merchant_id,
            aggregate_type="notification",
            aggregate_id=notification.id,
            event_type=EventType.NOTIFICATION_CREATED,
            payload={"notification_id": str(notification.id), "entity_id": str(order.id)},
        )
    )
    await session.commit()
    await session.refresh(order)
    return await serialize_order(OrderRepository(session), order, supplier.name)


# --- Generic Supplier CRUD Endpoints ---


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
    # The merchant dashboard is a marketplace catalogue, not a tenant-owned
    # supplier configuration list.  Supplier accounts therefore must remain
    # visible even though their ``merchant_id`` belongs to their own business.
    query = select(Supplier)
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
            select(func.count(SupplierProduct.id)).where(
                SupplierProduct.supplier_id == supplier.id,
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
                phone_number=supplier.phone_number,
                gstin=supplier.gstin,
                city=supplier.city,
                state=supplier.state,
                pincode=supplier.pincode,
                category=supplier.category,
            )
        )
    return CursorPage(items=items, next_cursor=next_cursor(rows, limit))


@router.get("/{supplier_id}", response_model=SupplierView)
async def get_supplier(
    supplier_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> SupplierView:
    supplier = await _supplier(session, supplier_id, principal.merchant_id)
    products = await _products(session, supplier.id, limit=20)
    product_count = await session.scalar(
        select(func.count(SupplierProduct.id)).where(
            SupplierProduct.supplier_id == supplier.id,
        )
    )
    return SupplierView(
        id=supplier.id,
        name=supplier.name,
        adapter_type=supplier.adapter_type,
        is_active=supplier.is_active,
        trust_score=supplier.trust_score,
        product_count=product_count or 0,
        phone_number=supplier.phone_number,
        gstin=supplier.gstin,
        city=supplier.city,
        state=supplier.state,
        pincode=supplier.pincode,
        category=supplier.category,
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
