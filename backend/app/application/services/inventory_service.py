from decimal import Decimal
from uuid import UUID

from app.infrastructure.db.repositories.inventory import InventoryRepository


class InventoryService:
    def __init__(self, repository: InventoryRepository) -> None:
        self.repository = repository

    async def list_inventory(self, merchant_id: UUID, store_id: UUID | None = None) -> list[dict]:
        rows = await self.repository.list(merchant_id, store_id)
        return [
            {
                "inventory_id": inventory.id,
                "store_id": inventory.store_id,
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "unit": product.unit,
                "quantity_on_hand": inventory.quantity_on_hand,
                "reorder_point": inventory.reorder_point,
                "is_low": inventory.quantity_on_hand <= inventory.reorder_point,
            }
            for inventory, product in rows
        ]

    async def record_event(
        self,
        *,
        merchant_id: UUID,
        store_id: UUID,
        product_id: UUID,
        quantity_delta: Decimal,
        event_type: str,
        source: str,
        idempotency_key: str,
    ) -> dict:
        inventory = await self.repository.apply_event(
            merchant_id=merchant_id,
            store_id=store_id,
            product_id=product_id,
            quantity_delta=quantity_delta,
            event_type=event_type,
            source=source,
            idempotency_key=idempotency_key,
        )
        return {"inventory_id": inventory.id, "quantity_on_hand": inventory.quantity_on_hand}
