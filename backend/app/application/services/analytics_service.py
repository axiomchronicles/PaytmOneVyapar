from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Inventory, Order, Sale


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self, merchant_id: UUID) -> dict:
        sales_quantity = await self.session.scalar(
            select(func.coalesce(func.sum(Sale.quantity), 0)).where(Sale.merchant_id == merchant_id)
        )
        low_inventory = await self.session.scalar(
            select(func.count(Inventory.id)).where(
                Inventory.merchant_id == merchant_id,
                Inventory.quantity_on_hand <= Inventory.reorder_point,
            )
        )
        orders = await self.session.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.merchant_id == merchant_id)
            .group_by(Order.status)
        )
        return {
            "sales_quantity": sales_quantity,
            "low_inventory_products": low_inventory,
            "orders_by_status": {status: count for status, count in orders},
        }
