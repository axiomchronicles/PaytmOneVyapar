from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.infrastructure.db.models import Inventory, InventoryEvent, Product, Store


class InventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self, merchant_id: UUID, store_id: UUID | None = None
    ) -> list[tuple[Inventory, Product]]:
        query = (
            select(Inventory, Product)
            .join(Product, Product.id == Inventory.product_id)
            .where(Inventory.merchant_id == merchant_id)
        )
        if store_id:
            query = query.where(Inventory.store_id == store_id)
        return list((await self.session.execute(query)).tuples())

    async def get_store(self, merchant_id: UUID, store_id: UUID) -> Store:
        store = await self.session.scalar(
            select(Store).where(Store.id == store_id, Store.merchant_id == merchant_id)
        )
        if store is None:
            raise NotFoundError("Store not found")
        return store

    async def merchant_products(
        self, merchant_id: UUID, *, for_update: bool = False
    ) -> Sequence[Product]:
        query = select(Product).where(Product.merchant_id == merchant_id)
        if for_update:
            query = query.with_for_update()
        return list(await self.session.scalars(query))

    async def add_product(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.flush()
        return product

    async def ensure_inventory(
        self, *, merchant_id: UUID, store_id: UUID, product_id: UUID
    ) -> Inventory:
        inventory = await self.session.scalar(
            select(Inventory)
            .where(
                Inventory.merchant_id == merchant_id,
                Inventory.store_id == store_id,
                Inventory.product_id == product_id,
            )
            .with_for_update()
        )
        if inventory is not None:
            return inventory
        inventory = Inventory(
            merchant_id=merchant_id,
            store_id=store_id,
            product_id=product_id,
            quantity_on_hand=Decimal("0"),
            reserved_quantity=Decimal("0"),
            reorder_point=Decimal("0"),
        )
        self.session.add(inventory)
        await self.session.flush()
        return inventory

    async def apply_event(
        self,
        *,
        merchant_id: UUID,
        store_id: UUID,
        product_id: UUID,
        quantity_delta: Decimal,
        event_type: str,
        source: str,
        idempotency_key: str,
        details: dict | None = None,
    ) -> Inventory:
        inventory = await self.session.scalar(
            select(Inventory)
            .where(
                Inventory.merchant_id == merchant_id,
                Inventory.store_id == store_id,
                Inventory.product_id == product_id,
            )
            .with_for_update()
        )
        if inventory is None:
            raise NotFoundError("Inventory record not found")
        updated = inventory.quantity_on_hand + quantity_delta
        if updated < 0:
            raise ValueError("Inventory cannot become negative")
        inventory.quantity_on_hand = updated
        self.session.add(
            InventoryEvent(
                merchant_id=merchant_id,
                store_id=store_id,
                product_id=product_id,
                event_type=event_type,
                quantity_delta=quantity_delta,
                quantity_after=updated,
                source=source,
                idempotency_key=idempotency_key,
                details=details or {},
            )
        )
        await self.session.flush()
        return inventory
