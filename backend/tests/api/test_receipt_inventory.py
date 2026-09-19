import asyncio
from decimal import Decimal
from uuid import uuid4

from conftest import MERCHANT_ID, PRODUCT_ID, STORE_ID
from sqlalchemy import func, select

from app.agents.receipt_schemas import ReceiptReviewResponse
from app.infrastructure.db.models import Inventory, InventoryEvent, Product


def _receipt_confidence() -> dict[str, float]:
    return {
        "supplier_name": 0.9,
        "invoice_number": 0.9,
        "invoice_date": 0,
        "currency": 0.99,
        "subtotal": 0,
        "tax": 0,
        "total": 0.9,
    }


def _item_confidence(value: float = 0.9) -> dict[str, float]:
    return {
        "name": value,
        "sku": value,
        "barcode": 0,
        "category": 0,
        "brand": 0,
        "description": 0,
        "quantity": value,
        "unit": value,
        "unit_price": value,
        "purchase_price": 0,
        "selling_price": 0,
        "mrp": 0,
        "gst_rate": 0,
        "tax_amount": 0,
        "discount": 0,
        "total_amount": value,
        "expiry_date": 0,
        "batch_number": 0,
    }


def _review() -> ReceiptReviewResponse:
    return ReceiptReviewResponse.model_validate(
        {
            "scan_id": str(uuid4()),
            "receipt": {
                "supplier_name": "Test Supplier",
                "invoice_number": "INV-10",
                "invoice_date": None,
                "currency": "INR",
                "subtotal": None,
                "tax": None,
                "total": "960",
                "field_confidence": _receipt_confidence(),
                "source_text": "Test Supplier INV-10 Total 960",
            },
            "items": [
                {
                    "line_id": str(uuid4()),
                    "name": "Cola crate",
                    "sku": "COLD-COLA-300",
                    "barcode": None,
                    "category": None,
                    "brand": None,
                    "description": None,
                    "quantity": "2",
                    "unit": "crate",
                    "unit_price": "480",
                    "purchase_price": None,
                    "selling_price": None,
                    "mrp": None,
                    "gst_rate": None,
                    "tax_amount": None,
                    "discount": None,
                    "total_amount": "960",
                    "expiry_date": None,
                    "batch_number": None,
                    "confidence": 0.95,
                    "field_confidence": _item_confidence(),
                    "source_text": "COLD-COLA-300 Cola crate 2 480 960",
                    "missing_fields": ["barcode"],
                    "low_confidence_fields": [],
                    "source_fields": ["name", "sku", "quantity", "unit", "unit_price"],
                }
            ],
            "detected_items": 1,
            "warnings": [],
            "image_preprocessed": False,
        }
    )


def _confirm_item(item, *, edited_fields: list[str]) -> dict:
    return {
        **item.model_dump(
            mode="json",
            exclude={
                "missing_fields",
                "low_confidence_fields",
                "source_fields",
                "matched_product_id",
                "match_type",
            },
        ),
        "edited_fields": edited_fields,
    }


class ReceiptWorkflowStub:
    def __init__(self, review: ReceiptReviewResponse) -> None:
        self.review = review

    async def extract(self, **kwargs) -> ReceiptReviewResponse:
        return self.review


def test_scan_receipt_returns_review_without_writing_inventory(client, auth_headers, db_factory):
    review = _review()
    client.app.state.receipt_extraction_workflow = ReceiptWorkflowStub(review)

    response = client.post(
        "/api/v1/inventory/scan-receipt",
        headers=auth_headers,
        files={"image": ("receipt.png", b"stub-image", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["matched_product_id"] == str(PRODUCT_ID)
    assert response.json()["status"] == "review_required"

    async def counts() -> tuple[int, int]:
        async with db_factory() as session:
            return (
                await session.scalar(select(func.count()).select_from(Product)),
                await session.scalar(select(func.count()).select_from(InventoryEvent)),
            )

    assert asyncio.run(counts()) == (1, 0)


def test_confirm_receipt_updates_existing_and_creates_new_atomically(
    client, auth_headers, db_factory
):
    review = _review()
    second = review.items[0].model_copy(
        update={
            "line_id": uuid4(),
            "name": "Tata Salt 1kg",
            "sku": "SALT-TATA-1KG",
            "quantity": 10.0,
            "unit": "piece",
            "unit_price": 28.0,
            "total_amount": 280.0,
            "matched_product_id": None,
            "match_type": None,
        }
    )
    body = {
        "scan_id": str(review.scan_id),
        "store_id": str(STORE_ID),
        "idempotency_key": "receipt-confirm-001",
        "receipt": review.receipt.model_dump(mode="json"),
        "items": [_confirm_item(item, edited_fields=[]) for item in [review.items[0], second]],
    }

    response = client.post(
        "/api/v1/inventory/scan-receipt/confirm", headers=auth_headers, json=body
    )
    assert response.status_code == 200, response.text
    assert response.json()["created_count"] == 1
    assert response.json()["updated_count"] == 1
    repeated = client.post(
        "/api/v1/inventory/scan-receipt/confirm", headers=auth_headers, json=body
    )
    assert repeated.status_code == 200
    assert repeated.json() == response.json()

    async def saved() -> tuple[Decimal, Decimal, int, int]:
        async with db_factory() as session:
            cola = await session.scalar(select(Inventory).where(Inventory.product_id == PRODUCT_ID))
            salt = await session.scalar(select(Product).where(Product.sku == "SALT-TATA-1KG"))
            salt_inventory = await session.scalar(
                select(Inventory).where(Inventory.product_id == salt.id)
            )
            product_count = await session.scalar(select(func.count()).select_from(Product))
            event_count = await session.scalar(select(func.count()).select_from(InventoryEvent))
            return (
                cola.quantity_on_hand,
                salt_inventory.quantity_on_hand,
                product_count,
                event_count,
            )

    assert asyncio.run(saved()) == (Decimal("5.000"), Decimal("10.000"), 2, 2)


def test_confirm_receipt_rolls_back_whole_batch_on_identity_conflict(
    client, auth_headers, db_factory
):
    other_product_id = uuid4()

    async def seed_barcode_product() -> None:
        async with db_factory() as session, session.begin():
            session.add(
                Product(
                    id=other_product_id,
                    merchant_id=MERCHANT_ID,
                    sku="OTHER-SKU",
                    name="Other",
                    unit="piece",
                    attributes={"barcode": "8901000000001"},
                )
            )

    asyncio.run(seed_barcode_product())
    review = _review()
    conflicting = review.items[0].model_copy(
        update={"line_id": uuid4(), "barcode": "8901000000001", "quantity": 1.0}
    )
    body = {
        "scan_id": str(review.scan_id),
        "store_id": str(STORE_ID),
        "idempotency_key": "receipt-confirm-conflict",
        "receipt": review.receipt.model_dump(mode="json"),
        "items": [
            _confirm_item(review.items[0], edited_fields=[]),
            _confirm_item(conflicting, edited_fields=["barcode"]),
        ],
    }

    response = client.post(
        "/api/v1/inventory/scan-receipt/confirm", headers=auth_headers, json=body
    )
    assert response.status_code == 400

    async def quantity() -> Decimal:
        async with db_factory() as session:
            inventory = await session.scalar(
                select(Inventory).where(Inventory.product_id == PRODUCT_ID)
            )
            return inventory.quantity_on_hand

    assert asyncio.run(quantity()) == Decimal("3.000")


def test_manual_inventory_add_uses_same_stock_event_path(client, auth_headers, db_factory):
    review = _review()
    item = review.items[0].model_copy(
        update={
            "line_id": uuid4(),
            "name": "Manual Tea Pack",
            "sku": "TEA-MANUAL-1",
            "quantity": 6.0,
            "unit": "pack",
            "purchase_price": 42.0,
            "selling_price": 50.0,
            "mrp": 55.0,
            "gst_rate": 5.0,
            "category": "Grocery",
            "source_text": None,
        }
    )
    body = {
        "batch_id": str(uuid4()),
        "store_id": str(STORE_ID),
        "idempotency_key": "manual-inventory-001",
        "items": [_confirm_item(item, edited_fields=list(_item_confidence()))],
    }

    response = client.post("/api/v1/inventory/manual", headers=auth_headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["created_count"] == 1

    async def saved() -> tuple[dict, str, Decimal]:
        async with db_factory() as session:
            product = await session.scalar(select(Product).where(Product.sku == "TEA-MANUAL-1"))
            event = await session.scalar(
                select(InventoryEvent).where(InventoryEvent.product_id == product.id)
            )
            return product.attributes, event.source, event.quantity_after

    attributes, source, quantity = asyncio.run(saved())
    assert Decimal(attributes["selling_price"]) == Decimal("50")
    assert Decimal(attributes["gst_rate"]) == Decimal("5")
    assert source == "MANUAL"
    assert quantity == Decimal("6.000")

    inventory = client.get("/api/v1/inventory", headers=auth_headers)
    manual = next(row for row in inventory.json() if row["sku"] == "TEA-MANUAL-1")
    assert Decimal(manual["purchase_price"]) == Decimal("42")
    assert Decimal(manual["selling_price"]) == Decimal("50")
    assert Decimal(manual["mrp"]) == Decimal("55")
    assert Decimal(manual["gst_rate"]) == Decimal("5")
