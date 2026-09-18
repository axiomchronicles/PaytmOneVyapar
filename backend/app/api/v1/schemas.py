from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorBody(APIModel):
    code: str
    message: str
    request_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(APIModel):
    error: ErrorBody


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"


class InventoryItemResponse(APIModel):
    inventory_id: UUID
    store_id: UUID
    product_id: UUID
    sku: str
    name: str
    unit: str
    quantity_on_hand: Decimal
    reorder_point: Decimal
    is_low: bool


class InventoryEventRequest(APIModel):
    store_id: UUID
    product_id: UUID
    quantity_delta: Decimal
    event_type: str
    source: str = "API"
    idempotency_key: str = Field(min_length=8, max_length=128)


class AgentRunRequest(APIModel):
    request_id: str = Field(min_length=8, max_length=128)
    store_id: UUID
    sku: str
    quantity_on_hand: float = Field(ge=0)
    reorder_point: float = Field(ge=0)
    safety_stock: float = Field(default=2, ge=0)
    required_quantity: float = Field(default=0, ge=0)
    unit: str = "crate"
    target_price: float = Field(gt=0)
    max_price: float = Field(gt=0)
    spending_limit: float = Field(gt=0)
    delivery_deadline: datetime
    sales_history: list[dict[str, Any]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_price_bounds(self) -> "AgentRunRequest":
        if self.target_price > self.max_price:
            raise ValueError("target_price cannot exceed max_price")
        return self


class ApprovalDecisionRequest(APIModel):
    approval_token: str = Field(min_length=20)
    request_id: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)


class ApprovalModificationRequest(APIModel):
    approval_token: str = Field(min_length=20)
    request_id: str = Field(min_length=8, max_length=128)
    quantity: Decimal | None = Field(default=None, gt=0)
    max_unit_price: Decimal | None = Field(default=None, gt=0)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ApprovalRejectRequest(APIModel):
    request_id: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)


class VoiceSessionRequest(APIModel):
    language_code: str = "auto"
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    encoding: str = "linear16"
    active_proposal_id: UUID | None = None
    active_request_id: str | None = None
    approval_token: str | None = None
