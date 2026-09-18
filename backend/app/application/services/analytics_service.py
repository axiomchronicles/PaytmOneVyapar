from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidRequestError
from app.infrastructure.db.models import Inventory, Merchant, Order, Product, Sale, Supplier


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def range(
        created_from: datetime | None, created_to: datetime | None
    ) -> tuple[datetime, datetime]:
        end = created_to or datetime.now(UTC)
        start = created_from or end - timedelta(days=30)
        if start >= end or end - start > timedelta(days=366):
            raise InvalidRequestError("Analytics date range must be positive and at most 366 days")
        return start, end

    async def overview(
        self,
        merchant_id: UUID,
        *,
        store_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> dict:
        start, end = self.range(created_from, created_to)
        sales_query = select(func.coalesce(func.sum(Sale.quantity), 0)).where(
            Sale.merchant_id == merchant_id,
            Sale.sold_at >= start,
            Sale.sold_at < end,
        )
        inventory_query = select(func.count(Inventory.id)).where(
            Inventory.merchant_id == merchant_id,
            Inventory.quantity_on_hand <= Inventory.reorder_point,
        )
        orders_query = select(Order.status, func.count(Order.id)).where(
            Order.merchant_id == merchant_id,
            Order.created_at >= start,
            Order.created_at < end,
        )
        if store_id:
            sales_query = sales_query.where(Sale.store_id == store_id)
            inventory_query = inventory_query.where(Inventory.store_id == store_id)
            orders_query = orders_query.where(Order.store_id == store_id)
        sales_quantity = await self.session.scalar(
            sales_query
        )
        low_inventory = await self.session.scalar(inventory_query)
        orders = await self.session.execute(
            orders_query.group_by(Order.status)
        )
        return {
            "sales_quantity": sales_quantity,
            "low_inventory_products": low_inventory,
            "orders_by_status": {status: count for status, count in orders},
            "range": {"from": start, "to": end},
        }

    async def sales(
        self,
        merchant_id: UUID,
        *,
        store_id: UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
        group_by: str,
    ) -> dict:
        start, end = self.range(created_from, created_to)
        if group_by not in {"day", "week", "month"}:
            raise InvalidRequestError("Sales grouping must be day, week, or month")
        dialect = self.session.bind.dialect.name if self.session.bind else "postgresql"
        if dialect == "postgresql":
            pattern = {"day": "YYYY-MM-DD", "week": "IYYY-\"W\"IW", "month": "YYYY-MM"}[
                group_by
            ]
            bucket = func.to_char(Sale.sold_at, pattern)
        elif group_by == "day":
            bucket = func.strftime("%Y-%m-%d", Sale.sold_at)
        elif group_by == "week":
            bucket = func.strftime("%Y-W%W", Sale.sold_at)
        else:
            bucket = func.strftime("%Y-%m", Sale.sold_at)
        query = select(
            bucket.label("bucket"),
            func.coalesce(func.sum(Sale.quantity * Sale.unit_price), 0).label("value"),
        ).where(
            Sale.merchant_id == merchant_id,
            Sale.sold_at >= start,
            Sale.sold_at < end,
        )
        if store_id:
            query = query.where(Sale.store_id == store_id)
        rows = (await self.session.execute(query.group_by(bucket).order_by(bucket))).all()
        currency = await self.session.scalar(
            select(Merchant.currency).where(Merchant.id == merchant_id)
        )
        return {
            "metric": "sales_value",
            "currency": currency or "INR",
            "group_by": group_by,
            "points": [{"bucket": str(label), "value": value} for label, value in rows],
        }

    async def inventory(self, merchant_id: UUID, *, store_id: UUID | None) -> dict:
        query = (
            select(
                func.coalesce(Product.category, "Uncategorized").label("label"),
                func.count(Inventory.id).label("products"),
                func.sum(case((Inventory.quantity_on_hand <= Inventory.reorder_point, 1), else_=0)).label(
                    "low_products"
                ),
            )
            .join(Product, Product.id == Inventory.product_id)
            .where(Inventory.merchant_id == merchant_id)
        )
        if store_id:
            query = query.where(Inventory.store_id == store_id)
        rows = (await self.session.execute(query.group_by(Product.category))).all()
        return {
            "categories": [
                {"category": label, "products": products, "low_products": low or 0}
                for label, products, low in rows
            ]
        }

    async def procurement(
        self,
        merchant_id: UUID,
        *,
        store_id: UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> dict:
        start, end = self.range(created_from, created_to)
        query = (
            select(
                Supplier.id,
                Supplier.name,
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_amount), 0),
            )
            .join(Supplier, Supplier.id == Order.supplier_id)
            .where(
                Order.merchant_id == merchant_id,
                Order.created_at >= start,
                Order.created_at < end,
            )
        )
        if store_id:
            query = query.where(Order.store_id == store_id)
        rows = (await self.session.execute(query.group_by(Supplier.id, Supplier.name))).all()
        currency = await self.session.scalar(
            select(Merchant.currency).where(Merchant.id == merchant_id)
        )
        return {
            "currency": currency or "INR",
            "suppliers": [
                {
                    "supplier_id": supplier_id,
                    "supplier_name": name,
                    "order_count": count,
                    "spend": spend,
                }
                for supplier_id, name, count, spend in rows
            ],
        }
