from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ApprovalStatus, OrderStatus


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)


class InventorySnapshot(DomainModel):
    product_id: UUID | None = None
    sku: str
    quantity_on_hand: Decimal = Field(ge=0)
    reorder_point: Decimal = Field(ge=0)
    captured_at: datetime


class ForecastResult(DomainModel):
    predicted_demand: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    forecast_horizon_days: int = Field(gt=0)
    model_name: str
    feature_snapshot: dict[str, Any]


class PurchaseRequest(DomainModel):
    sku: str
    quantity: Decimal = Field(gt=0)
    unit: str
    target_price: Decimal = Field(gt=0)
    max_price: Decimal = Field(gt=0)
    delivery_deadline: datetime
    merchant_id: UUID
    store_id: UUID

    @model_validator(mode="after")
    def check_price_limit(self) -> "PurchaseRequest":
        if self.target_price > self.max_price:
            raise ValueError("target_price cannot exceed max_price")
        return self


class SupplierQuote(DomainModel):
    supplier_id: UUID
    supplier_name: str
    sku: str
    available_quantity: Decimal = Field(ge=0)
    unit_price: Decimal = Field(gt=0)
    currency: str = "INR"
    delivery_at: datetime
    quote_id: str
    expires_at: datetime


class RiskResult(DomainModel):
    passed: bool
    reasons: tuple[str, ...] = ()
    checks: dict[str, bool] = Field(default_factory=dict)


class PurchaseProposal(DomainModel):
    proposal_id: UUID
    merchant_id: UUID
    store_id: UUID
    supplier_id: UUID
    sku: str
    quantity: Decimal = Field(gt=0)
    unit: str
    unit_price: Decimal = Field(gt=0)
    currency: str = "INR"
    delivery_at: datetime
    quote_id: str

    @property
    def total_amount(self) -> Decimal:
        return self.quantity * self.unit_price

    def canonical_payload(self) -> dict[str, str]:
        return {
            "proposal_id": str(self.proposal_id),
            "merchant_id": str(self.merchant_id),
            "store_id": str(self.store_id),
            "supplier_id": str(self.supplier_id),
            "sku": self.sku,
            "quantity": str(self.quantity),
            "unit": self.unit,
            "unit_price": str(self.unit_price),
            "currency": self.currency,
            "delivery_at": self.delivery_at.isoformat(),
            "quote_id": self.quote_id,
        }


class ApprovalRecord(DomainModel):
    approval_id: UUID
    proposal_id: UUID
    merchant_id: UUID
    order_hash: str
    nonce: str
    status: ApprovalStatus
    expires_at: datetime


class OrderResult(DomainModel):
    order_id: UUID
    status: OrderStatus
    supplier_confirmation: str | None = None
    transaction_id: UUID | None = None
