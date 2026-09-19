from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Confidence = Annotated[float, Field(ge=0, le=1)]
NonNegativeNumber = Annotated[float, Field(ge=0)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ReceiptModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReceiptFieldConfidence(ReceiptModel):
    supplier_name: Confidence
    invoice_number: Confidence
    invoice_date: Confidence
    currency: Confidence
    subtotal: Confidence
    tax: Confidence
    total: Confidence


class ItemFieldConfidence(ReceiptModel):
    name: Confidence
    sku: Confidence
    barcode: Confidence
    category: Confidence
    brand: Confidence
    description: Confidence
    quantity: Confidence
    unit: Confidence
    unit_price: Confidence
    purchase_price: Confidence
    selling_price: Confidence
    mrp: Confidence
    gst_rate: Confidence
    tax_amount: Confidence
    discount: Confidence
    total_amount: Confidence
    expiry_date: Confidence
    batch_number: Confidence


class ReceiptMetadata(ReceiptModel):
    supplier_name: str | None
    invoice_number: str | None
    invoice_date: date | None
    currency: str | None
    subtotal: NonNegativeNumber | None
    tax: NonNegativeNumber | None
    total: NonNegativeNumber | None
    field_confidence: ReceiptFieldConfidence
    source_text: str | None


class ExtractedInventoryItem(ReceiptModel):
    name: str | None
    sku: str | None
    barcode: str | None
    category: str | None
    brand: str | None
    description: str | None
    quantity: NonNegativeNumber | None
    unit: str | None
    unit_price: NonNegativeNumber | None
    purchase_price: NonNegativeNumber | None
    selling_price: NonNegativeNumber | None
    mrp: NonNegativeNumber | None
    gst_rate: Annotated[float, Field(ge=0, le=100)] | None
    tax_amount: NonNegativeNumber | None
    discount: NonNegativeNumber | None
    total_amount: NonNegativeNumber | None
    expiry_date: date | None
    batch_number: str | None
    confidence: Confidence
    field_confidence: ItemFieldConfidence
    source_text: str | None


class VisionReceiptExtraction(ReceiptModel):
    receipt: ReceiptMetadata
    items: Annotated[list[ExtractedInventoryItem], Field(max_length=500)]
    warnings: Annotated[list[str], Field(max_length=30)]


class ReceiptReviewItem(ExtractedInventoryItem):
    line_id: UUID
    missing_fields: list[str]
    low_confidence_fields: list[str]
    source_fields: list[str]
    matched_product_id: UUID | None = None
    match_type: Literal["sku", "barcode"] | None = None


class ReceiptReviewResponse(ReceiptModel):
    scan_id: UUID
    status: Literal["review_required"] = "review_required"
    receipt: ReceiptMetadata
    items: list[ReceiptReviewItem]
    detected_items: int
    warnings: list[str]
    image_preprocessed: bool


class ReceiptConfirmItem(ReceiptModel):
    line_id: UUID
    name: RequiredText
    sku: RequiredText
    barcode: str | None = None
    category: str | None = None
    brand: str | None = None
    description: str | None = None
    quantity: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
    unit: RequiredText
    unit_price: NonNegativeMoney | None = None
    purchase_price: NonNegativeMoney | None = None
    selling_price: NonNegativeMoney | None = None
    mrp: NonNegativeMoney | None = None
    gst_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=6, decimal_places=3)] | None = None
    tax_amount: NonNegativeMoney | None = None
    discount: NonNegativeMoney | None = None
    total_amount: NonNegativeMoney | None = None
    expiry_date: date | None = None
    batch_number: str | None = None
    confidence: Confidence = 0
    field_confidence: ItemFieldConfidence
    source_text: str | None = None
    edited_fields: list[str] = Field(default_factory=list, max_length=18)


class ReceiptConfirmRequest(ReceiptModel):
    scan_id: UUID
    store_id: UUID
    idempotency_key: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=128)
    ]
    receipt: ReceiptMetadata
    items: Annotated[list[ReceiptConfirmItem], Field(min_length=1, max_length=500)]


class ManualInventoryRequest(ReceiptModel):
    batch_id: UUID
    store_id: UUID
    idempotency_key: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=128)
    ]
    items: Annotated[list[ReceiptConfirmItem], Field(min_length=1, max_length=500)]


class ConfirmedInventoryItem(ReceiptModel):
    line_id: UUID
    action: Literal["created", "updated"]
    inventory_id: UUID
    product_id: UUID
    sku: str
    name: str
    unit: str
    quantity_added: Decimal
    quantity_on_hand: Decimal


class ReceiptConfirmResponse(ReceiptModel):
    scan_id: UUID
    status: Literal["confirmed"] = "confirmed"
    created_count: int
    updated_count: int
    items: list[ConfirmedInventoryItem]
