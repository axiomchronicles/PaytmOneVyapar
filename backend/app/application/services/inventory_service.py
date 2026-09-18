from decimal import Decimal
from uuid import UUID

from app.domain.enums import NotificationType
from app.domain.events import EventType
from app.infrastructure.db.models import Notification, OutboxEvent
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
        self.repository.session.add(
            OutboxEvent(
                merchant_id=merchant_id,
                aggregate_type="inventory",
                aggregate_id=inventory.id,
                event_type=EventType.INVENTORY_UPDATED,
                payload={
                    "inventory_id": str(inventory.id),
                    "store_id": str(store_id),
                    "product_id": str(product_id),
                    "quantity_on_hand": str(inventory.quantity_on_hand),
                },
            )
        )
        if inventory.quantity_on_hand <= inventory.reorder_point:
            notification = Notification(
                merchant_id=merchant_id,
                notification_type=NotificationType.INVENTORY_ALERT,
                title="Inventory needs attention",
                body="Stock is at or below its reorder point.",
                entity_type="inventory",
                entity_id=inventory.id,
                payload={"store_id": str(store_id), "product_id": str(product_id)},
            )
            self.repository.session.add(notification)
            await self.repository.session.flush()
            self.repository.session.add(
                OutboxEvent(
                    merchant_id=merchant_id,
                    aggregate_type="notification",
                    aggregate_id=notification.id,
                    event_type=EventType.NOTIFICATION_CREATED,
                    payload={
                        "notification_id": str(notification.id),
                        "notification_type": notification.notification_type,
                        "entity_type": "inventory",
                        "entity_id": str(inventory.id),
                    },
                )
            )
        return {"inventory_id": inventory.id, "quantity_on_hand": inventory.quantity_on_hand}
