from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.infrastructure.db.models import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, order_id: UUID) -> Order:
        order = await self.session.get(Order, order_id)
        if order is None:
            raise NotFoundError("Order not found")
        return order

    async def by_idempotency_key(self, merchant_id: UUID, key: str) -> Order | None:
        return await self.session.scalar(
            select(Order).where(Order.merchant_id == merchant_id, Order.idempotency_key == key)
        )

    async def add(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return order
