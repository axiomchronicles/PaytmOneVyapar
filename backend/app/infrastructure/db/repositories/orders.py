from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.infrastructure.db.models import Order, OrderEvent, OrderItem, Supplier


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, order_id: UUID) -> Order:
        order = await self.session.get(Order, order_id)
        if order is None:
            raise NotFoundError("Order not found")
        return order

    async def get_for_merchant(self, order_id: UUID, merchant_id: UUID) -> Order:
        order = await self.session.scalar(
            select(Order).where(Order.id == order_id, Order.merchant_id == merchant_id)
        )
        if order is None:
            raise NotFoundError("Order not found")
        return order

    async def list_orders(
        self,
        merchant_id: UUID,
        *,
        status: str | None,
        store_id: UUID | None,
        supplier_id: UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
        search: str | None,
        cursor: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[tuple[Order, Supplier]]:
        query = select(Order, Supplier).join(Supplier, Supplier.id == Order.supplier_id).where(
            Order.merchant_id == merchant_id
        )
        if status:
            query = query.where(Order.status == status)
        if store_id:
            query = query.where(Order.store_id == store_id)
        if supplier_id:
            query = query.where(Order.supplier_id == supplier_id)
        if created_from:
            query = query.where(Order.created_at >= created_from)
        if created_to:
            query = query.where(Order.created_at < created_to)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(Supplier.name.ilike(pattern), Order.supplier_reference.ilike(pattern))
            )
        if cursor:
            created_at, row_id = cursor
            query = query.where(
                or_(
                    Order.created_at < created_at,
                    and_(Order.created_at == created_at, Order.id < row_id),
                )
            )
        return list(
            (await self.session.execute(
                query.order_by(Order.created_at.desc(), Order.id.desc()).limit(limit + 1)
            )).tuples()
        )

    async def supplier(self, supplier_id: UUID) -> Supplier:
        supplier = await self.session.get(Supplier, supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier not found")
        return supplier

    async def items(self, order_id: UUID) -> list[OrderItem]:
        return list(
            await self.session.scalars(
                select(OrderItem)
                .where(OrderItem.order_id == order_id)
                .order_by(OrderItem.created_at, OrderItem.id)
            )
        )

    async def timeline(self, order_id: UUID, merchant_id: UUID) -> list[OrderEvent]:
        return list(
            await self.session.scalars(
                select(OrderEvent)
                .where(OrderEvent.order_id == order_id, OrderEvent.merchant_id == merchant_id)
                .order_by(OrderEvent.created_at, OrderEvent.id)
            )
        )

    async def by_idempotency_key(self, merchant_id: UUID, key: str) -> Order | None:
        return await self.session.scalar(
            select(Order).where(Order.merchant_id == merchant_id, Order.idempotency_key == key)
        )

    async def add(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return order
