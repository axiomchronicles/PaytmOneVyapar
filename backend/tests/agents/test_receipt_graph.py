from io import BytesIO

import pytest
from PIL import Image

from app.agents.receipt_graph import ReceiptExtractionWorkflow
from app.agents.receipt_schemas import VisionReceiptExtraction
from app.core.errors import InvalidRequestError


def _item_confidence(**updates) -> dict[str, float]:
    values = {
        "name": 0,
        "sku": 0,
        "barcode": 0,
        "category": 0,
        "brand": 0,
        "description": 0,
        "quantity": 0,
        "unit": 0,
        "unit_price": 0,
        "purchase_price": 0,
        "selling_price": 0,
        "mrp": 0,
        "gst_rate": 0,
        "tax_amount": 0,
        "discount": 0,
        "total_amount": 0,
        "expiry_date": 0,
        "batch_number": 0,
    }
    values.update(updates)
    return values


def _receipt_confidence() -> dict[str, float]:
    return {
        "supplier_name": 0,
        "invoice_number": 0,
        "invoice_date": 0,
        "currency": 0.95,
        "subtotal": 0,
        "tax": 0,
        "total": 0.9,
    }


class VisionStub:
    def __init__(self) -> None:
        self.messages = None

    async def structured(self, messages, schema):
        self.messages = messages
        assert schema is VisionReceiptExtraction
        return VisionReceiptExtraction.model_validate(
            {
                "receipt": {
                    "supplier_name": None,
                    "invoice_number": None,
                    "invoice_date": None,
                    "currency": "₹",
                    "subtotal": None,
                    "tax": None,
                    "total": "280",
                    "field_confidence": _receipt_confidence(),
                    "source_text": "Total ₹280",
                },
                "items": [
                    {
                        "name": "  Tata   Salt 1kg ",
                        "sku": None,
                        "barcode": None,
                        "category": None,
                        "brand": "Tata",
                        "description": None,
                        "quantity": "10",
                        "unit": "pcs",
                        "unit_price": "28",
                        "purchase_price": None,
                        "selling_price": None,
                        "mrp": None,
                        "gst_rate": None,
                        "tax_amount": None,
                        "discount": None,
                        "total_amount": "280",
                        "expiry_date": None,
                        "batch_number": None,
                        "confidence": 0.96,
                        "field_confidence": _item_confidence(
                            name=0.99,
                            brand=0.8,
                            quantity=0.98,
                            unit=0.7,
                            unit_price=0.97,
                            total_amount=0.99,
                        ),
                        "source_text": "Tata Salt 1kg 10 28 280",
                    }
                ],
                "warnings": [],
            }
        )


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (120, 160), "white").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_receipt_graph_uses_multimodal_structured_output_and_preserves_missing_fields():
    provider = VisionStub()
    review = await ReceiptExtractionWorkflow(provider).extract(
        filename="receipt.png", content_type="image/png", content=_png()
    )

    assert review.detected_items == 1
    assert review.receipt.currency == "INR"
    assert review.items[0].name == "Tata Salt 1kg"
    assert review.items[0].unit == "piece"
    assert review.items[0].sku is None
    assert "sku" in review.items[0].missing_fields
    assert "unit" in review.items[0].low_confidence_fields
    assert provider.messages[1]["content"][1]["type"] == "image_url"
    assert provider.messages[1]["content"][1]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )


@pytest.mark.asyncio
async def test_receipt_graph_rejects_non_image_before_calling_provider():
    provider = VisionStub()
    with pytest.raises(InvalidRequestError, match="JPEG, PNG, or WebP"):
        await ReceiptExtractionWorkflow(provider).extract(
            filename="receipt.txt", content_type="text/plain", content=b"not an image"
        )
    assert provider.messages is None
