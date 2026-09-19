import hashlib
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.agents.receipt_schemas import (
    ConfirmedInventoryItem,
    ManualInventoryRequest,
    ReceiptConfirmRequest,
    ReceiptConfirmResponse,
    ReceiptReviewResponse,
)
from app.application.services.audit_service import AuditService
from app.core.errors import ConflictError, InvalidRequestError
from app.core.security import canonical_order_hash
from app.domain.enums import NotificationType
from app.domain.events import EventType
from app.infrastructure.db.models import IdempotencyKey, Notification, OutboxEvent, Product
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
                "category": product.category,
                "barcode": (product.attributes or {}).get("barcode"),
                "brand": (product.attributes or {}).get("brand"),
                "description": (product.attributes or {}).get("description"),
                "unit_price": (product.attributes or {}).get("last_unit_price"),
                "purchase_price": (product.attributes or {}).get("last_purchase_price"),
                "selling_price": (product.attributes or {}).get("selling_price"),
                "mrp": (product.attributes or {}).get("mrp"),
                "gst_rate": (product.attributes or {}).get("gst_rate"),
                "expiry_date": (product.attributes or {}).get("expiry_date"),
                "batch_number": (product.attributes or {}).get("batch_number"),
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
        details: dict | None = None,
    ) -> dict:
        inventory = await self.repository.apply_event(
            merchant_id=merchant_id,
            store_id=store_id,
            product_id=product_id,
            quantity_delta=quantity_delta,
            event_type=event_type,
            source=source,
            idempotency_key=idempotency_key,
            details=details,
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

    async def match_receipt_products(
        self, merchant_id: UUID, review: ReceiptReviewResponse
    ) -> ReceiptReviewResponse:
        products = await self.repository.merchant_products(merchant_id)
        by_sku, by_barcode = self._product_indexes(products)
        matched = []
        for item in review.items:
            sku_matches = by_sku.get(item.sku.casefold(), []) if item.sku else []
            product = sku_matches[0] if len(sku_matches) == 1 else None
            match_type = "sku" if product else None
            if product is None and item.barcode:
                barcode_matches = by_barcode.get(item.barcode.strip(), [])
                product = barcode_matches[0] if len(barcode_matches) == 1 else None
                match_type = "barcode" if product else None
            matched.append(
                item.model_copy(
                    update={
                        "matched_product_id": product.id if product else None,
                        "match_type": match_type,
                    }
                )
            )
        return review.model_copy(update={"items": matched})

    async def confirm_receipt(
        self,
        *,
        merchant_id: UUID,
        user_id: UUID,
        request: ReceiptConfirmRequest,
        trace_id: str | None = None,
        event_source: str = "RECEIPT_SCAN",
        audit_action: str = "inventory.receipt_confirmed",
        idempotency_scope: str = "inventory-receipt",
    ) -> ReceiptConfirmResponse:
        idempotency, cached = await self._begin_confirmation(
            merchant_id,
            request,
            scope_prefix=idempotency_scope,
        )
        if cached is not None:
            return ReceiptConfirmResponse.model_validate(cached)

        await self.repository.get_store(merchant_id, request.store_id)
        products = await self.repository.merchant_products(merchant_id, for_update=True)
        by_sku, by_barcode = self._product_indexes(products)

        results: list[ConfirmedInventoryItem] = []
        for index, item in enumerate(request.items):
            normalized_sku = item.sku.strip().upper()
            normalized_barcode = item.barcode.strip() if item.barcode else None
            sku_matches = by_sku.get(normalized_sku.casefold(), [])
            barcode_matches = by_barcode.get(normalized_barcode, []) if normalized_barcode else []
            if len(sku_matches) > 1 or len(barcode_matches) > 1:
                raise InvalidRequestError(
                    "Multiple existing products match the reviewed identifiers",
                    details={"line_id": str(item.line_id)},
                )
            sku_match = sku_matches[0] if sku_matches else None
            barcode_match = barcode_matches[0] if barcode_matches else None
            if sku_match and barcode_match and sku_match.id != barcode_match.id:
                raise InvalidRequestError(
                    "The reviewed SKU and barcode identify different existing products",
                    details={"line_id": str(item.line_id)},
                )

            product = sku_match or barcode_match
            created = product is None
            stable_attributes = self._stable_product_attributes(item)
            if product is None:
                product = await self.repository.add_product(
                    Product(
                        merchant_id=merchant_id,
                        sku=normalized_sku,
                        name=item.name.strip(),
                        unit=item.unit.strip(),
                        category=self._clean_optional(item.category),
                        attributes=stable_attributes,
                    )
                )
                by_sku.setdefault(product.sku.casefold(), []).append(product)
                if normalized_barcode:
                    by_barcode.setdefault(normalized_barcode, []).append(product)
            else:
                product.name = item.name.strip()
                product.unit = item.unit.strip()
                if category := self._clean_optional(item.category):
                    product.category = category
                product.attributes = {**(product.attributes or {}), **stable_attributes}

            await self.repository.ensure_inventory(
                merchant_id=merchant_id,
                store_id=request.store_id,
                product_id=product.id,
            )
            event = await self.record_event(
                merchant_id=merchant_id,
                store_id=request.store_id,
                product_id=product.id,
                quantity_delta=item.quantity,
                event_type="STOCK_RECEIVED",
                source=event_source,
                idempotency_key=self._event_idempotency_key(
                    request.idempotency_key, item.line_id, index
                ),
                details={
                    "scan_id": str(request.scan_id),
                    "line_id": str(item.line_id),
                    "receipt": (
                        request.receipt.model_dump(mode="json")
                        if event_source == "RECEIPT_SCAN"
                        else None
                    ),
                    "reviewed_item": item.model_dump(mode="json"),
                    "matched_by": "sku" if sku_match else "barcode" if barcode_match else None,
                },
            )
            results.append(
                ConfirmedInventoryItem(
                    line_id=item.line_id,
                    action="created" if created else "updated",
                    inventory_id=event["inventory_id"],
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    unit=product.unit,
                    quantity_added=item.quantity,
                    quantity_on_hand=event["quantity_on_hand"],
                )
            )

        response = ReceiptConfirmResponse(
            scan_id=request.scan_id,
            created_count=sum(item.action == "created" for item in results),
            updated_count=sum(item.action == "updated" for item in results),
            items=results,
        )
        await AuditService(self.repository.session).record(
            action=audit_action,
            actor_type="USER",
            actor_id=str(user_id),
            resource_type="receipt_scan",
            resource_id=str(request.scan_id),
            merchant_id=merchant_id,
            trace_id=trace_id,
            metadata={
                "store_id": str(request.store_id),
                "created_count": response.created_count,
                "updated_count": response.updated_count,
                "item_count": len(response.items),
            },
        )
        idempotency.status = "COMPLETED"
        idempotency.response = jsonable_encoder(response)
        return response

    async def confirm_manual_inventory(
        self,
        *,
        merchant_id: UUID,
        user_id: UUID,
        request: ManualInventoryRequest,
        trace_id: str | None = None,
    ) -> ReceiptConfirmResponse:
        empty_confidence = {
            "supplier_name": 0,
            "invoice_number": 0,
            "invoice_date": 0,
            "currency": 0,
            "subtotal": 0,
            "tax": 0,
            "total": 0,
        }
        receipt_request = ReceiptConfirmRequest.model_validate(
            {
                "scan_id": request.batch_id,
                "store_id": request.store_id,
                "idempotency_key": request.idempotency_key,
                "receipt": {
                    "supplier_name": None,
                    "invoice_number": None,
                    "invoice_date": None,
                    "currency": None,
                    "subtotal": None,
                    "tax": None,
                    "total": None,
                    "field_confidence": empty_confidence,
                    "source_text": None,
                },
                "items": [item.model_dump(mode="json") for item in request.items],
            }
        )
        return await self.confirm_receipt(
            merchant_id=merchant_id,
            user_id=user_id,
            request=receipt_request,
            trace_id=trace_id,
            event_source="MANUAL",
            audit_action="inventory.manual_confirmed",
            idempotency_scope="inventory-manual",
        )

    async def _begin_confirmation(
        self,
        merchant_id: UUID,
        request: ReceiptConfirmRequest,
        *,
        scope_prefix: str,
    ) -> tuple[IdempotencyKey, dict[str, Any] | None]:
        scope = f"{scope_prefix}:{merchant_id}"
        request_hash = canonical_order_hash(request.model_dump(mode="json"))
        row = await self.repository.session.scalar(
            select(IdempotencyKey)
            .where(IdempotencyKey.scope == scope, IdempotencyKey.key == request.idempotency_key)
            .with_for_update()
        )
        if row is not None:
            if row.request_hash != request_hash:
                raise ConflictError("Idempotency key was reused with different receipt data")
            if row.status == "COMPLETED" and row.response is not None:
                return row, row.response
            raise ConflictError("This receipt confirmation is already being processed")
        row = IdempotencyKey(
            scope=scope,
            key=request.idempotency_key,
            request_hash=request_hash,
        )
        self.repository.session.add(row)
        await self.repository.session.flush()
        return row, None

    @staticmethod
    def _product_barcode(product: Product) -> str | None:
        value = (product.attributes or {}).get("barcode")
        return str(value).strip() if value is not None and str(value).strip() else None

    @classmethod
    def _product_indexes(
        cls, products
    ) -> tuple[dict[str, list[Product]], dict[str, list[Product]]]:
        by_sku: dict[str, list[Product]] = {}
        by_barcode: dict[str, list[Product]] = {}
        for product in products:
            by_sku.setdefault(product.sku.casefold(), []).append(product)
            if barcode := cls._product_barcode(product):
                by_barcode.setdefault(barcode, []).append(product)
        return by_sku, by_barcode

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        cleaned = value.strip() if value else ""
        return cleaned or None

    def _stable_product_attributes(self, item) -> dict[str, Any]:
        values = {
            "barcode": self._clean_optional(item.barcode),
            "brand": self._clean_optional(item.brand),
            "description": self._clean_optional(item.description),
            "selling_price": item.selling_price,
            "mrp": item.mrp,
            "gst_rate": item.gst_rate,
            "last_purchase_price": item.purchase_price,
            "last_unit_price": item.unit_price,
            "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
            "batch_number": self._clean_optional(item.batch_number),
        }
        return {
            key: str(value) if isinstance(value, Decimal) else value
            for key, value in values.items()
            if value is not None
        }

    @staticmethod
    def _event_idempotency_key(key: str, line_id: UUID, index: int) -> str:
        digest = hashlib.sha256(f"{key}:{line_id}:{index}".encode()).hexdigest()
        return f"receipt:{digest}"
