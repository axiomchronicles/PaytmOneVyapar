import base64
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from app.agents.receipt_image import prepare_receipt_image, validate_receipt_image
from app.agents.receipt_schemas import (
    ExtractedInventoryItem,
    ReceiptMetadata,
    ReceiptReviewItem,
    ReceiptReviewResponse,
    VisionReceiptExtraction,
)
from app.core.errors import InvalidRequestError, ProviderError
from app.domain.contracts import LLMProvider

ITEM_FIELDS = (
    "name",
    "sku",
    "barcode",
    "category",
    "brand",
    "description",
    "quantity",
    "unit",
    "unit_price",
    "purchase_price",
    "selling_price",
    "mrp",
    "gst_rate",
    "tax_amount",
    "discount",
    "total_amount",
    "expiry_date",
    "batch_number",
)
LOW_CONFIDENCE_THRESHOLD = 0.75

SYSTEM_PROMPT = """You extract inventory line items from Indian merchant receipts, invoices, and
product lists. Return only the requested structured schema. Inspect the entire image from top to
bottom and include every visible product line, even when the document is long.

Evidence rules:
- Never infer, estimate, or invent business data.
- Use null for every field not explicitly visible or not reliably attributable to that line item.
- Do not guess SKU, barcode, category, brand, GST, selling price, MRP, unit, dates, or batch number.
- Do not copy a receipt-level value into an item unless it is explicitly tied to that item.
- A printed rate belongs in unit_price. Only populate purchase_price when the document explicitly
  identifies it as a purchase/cost price. Never copy purchase price into selling price.
- Preserve the visible line in source_text. Set each field confidence from 0 to 1; missing fields
  must have confidence 0. The item confidence is the confidence that the row is a product line.
- The rupee symbol or an explicit INR/Rs currency marker may be normalized to INR.
- Numeric fields contain numbers only. Dates use YYYY-MM-DD only when readable.
- warnings contains only concrete readability, ambiguity, or reconciliation issues.
"""


def validate_image(state: dict[str, Any]) -> dict[str, Any]:
    return validate_receipt_image(state)


def prepare_document(state: dict[str, Any]) -> dict[str, Any]:
    return prepare_receipt_image(state)


async def vision_extraction(state: dict[str, Any], *, llm_provider: LLMProvider) -> dict[str, Any]:
    encoded = base64.b64encode(state["prepared_image_bytes"]).decode("ascii")
    data_url = f"data:{state['prepared_content_type']};base64,{encoded}"
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Extract all inventory items and receipt metadata from this image. "
                        "Review the full document before responding."
                    ),
                },
                {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
            ],
        },
    ]
    try:
        result = await llm_provider.structured(messages, VisionReceiptExtraction)
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError("Receipt extraction is temporarily unavailable") from exc
    return {"vision_result": result}


def parse_structured_output(state: dict[str, Any]) -> dict[str, Any]:
    result = state.get("vision_result")
    if isinstance(result, VisionReceiptExtraction):
        parsed = result
    elif isinstance(result, BaseModel):
        parsed = VisionReceiptExtraction.model_validate(result.model_dump())
    else:
        try:
            parsed = VisionReceiptExtraction.model_validate(result)
        except Exception as exc:
            raise ProviderError("The vision model returned an invalid receipt structure") from exc
    return {"parsed_extraction": parsed}


def validate_extracted_data(state: dict[str, Any]) -> dict[str, Any]:
    extraction = state["parsed_extraction"]
    if not extraction.items:
        raise InvalidRequestError(
            "No product lines were detected in this image",
            details={"reason": "no_inventory_items"},
        )
    return {"parsed_extraction": extraction}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned or None


def _normalize_unit(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    aliases = {
        "pc": "piece",
        "pcs": "piece",
        "pieces": "piece",
        "piece": "piece",
        "kgs": "kg",
        "kilogram": "kg",
        "kilograms": "kg",
        "grams": "g",
        "gram": "g",
        "litre": "l",
        "litres": "l",
        "liter": "l",
        "liters": "l",
        "millilitre": "ml",
        "millilitres": "ml",
        "milliliter": "ml",
        "milliliters": "ml",
    }
    return aliases.get(cleaned.casefold(), cleaned)


def _normalize_receipt(receipt: ReceiptMetadata) -> ReceiptMetadata:
    currency = _clean_text(receipt.currency)
    if currency is not None:
        aliases = {"₹": "INR", "rs": "INR", "rs.": "INR", "inr": "INR"}
        currency = aliases.get(currency.casefold(), currency.upper())
    return receipt.model_copy(
        update={
            "supplier_name": _clean_text(receipt.supplier_name),
            "invoice_number": _clean_text(receipt.invoice_number),
            "currency": currency,
            "source_text": _clean_text(receipt.source_text),
        }
    )


def _normalize_item(item: ExtractedInventoryItem) -> ExtractedInventoryItem:
    updates = {
        field: _clean_text(getattr(item, field))
        for field in (
            "name",
            "sku",
            "barcode",
            "category",
            "brand",
            "description",
            "batch_number",
            "source_text",
        )
    }
    updates["unit"] = _normalize_unit(item.unit)
    return item.model_copy(update=updates)


def normalize_products(state: dict[str, Any]) -> dict[str, Any]:
    extraction = state["parsed_extraction"]
    normalized = extraction.model_copy(
        update={
            "receipt": _normalize_receipt(extraction.receipt),
            "items": [_normalize_item(item) for item in extraction.items],
            "warnings": [
                warning for raw in extraction.warnings if (warning := _clean_text(raw)) is not None
            ],
        }
    )
    return {"normalized_extraction": normalized}


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _numeric_mismatch(item: ExtractedInventoryItem) -> bool:
    if item.quantity is None or item.unit_price is None or item.total_amount is None:
        return False
    expected = item.quantity * item.unit_price
    tolerance = max(0.05, item.total_amount * 0.01)
    return abs(expected - item.total_amount) > tolerance


def detect_missing_fields(state: dict[str, Any]) -> dict[str, Any]:
    extraction = state["normalized_extraction"]
    review_items: list[dict[str, Any]] = []
    warnings = list(extraction.warnings)
    for index, item in enumerate(extraction.items, start=1):
        missing = [field for field in ITEM_FIELDS if _is_missing(getattr(item, field))]
        confidence = item.field_confidence.model_dump()
        low_confidence = [
            field
            for field in ITEM_FIELDS
            if field not in missing and confidence[field] < LOW_CONFIDENCE_THRESHOLD
        ]
        source_fields = [field for field in ITEM_FIELDS if field not in missing]
        if _numeric_mismatch(item):
            warnings.append(
                f"Line {index} quantity × unit price does not match its printed total; values were preserved."
            )
            low_confidence = sorted(
                set(low_confidence) | {"quantity", "unit_price", "total_amount"}
            )
        review_items.append(
            {
                **item.model_dump(),
                "line_id": uuid4(),
                "missing_fields": missing,
                "low_confidence_fields": low_confidence,
                "source_fields": source_fields,
            }
        )
    return {"review_items": review_items, "normalized_extraction": extraction, "warnings": warnings}


def prepare_review_payload(state: dict[str, Any]) -> dict[str, Any]:
    extraction = state["normalized_extraction"]
    items = [ReceiptReviewItem.model_validate(item) for item in state["review_items"]]
    payload = ReceiptReviewResponse(
        scan_id=uuid4(),
        receipt=extraction.receipt,
        items=items,
        detected_items=len(items),
        warnings=state.get("warnings", extraction.warnings),
        image_preprocessed=state.get("image_preprocessed", False),
    )
    return {"review_payload": payload}
