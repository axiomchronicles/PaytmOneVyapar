import re
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.domain.enums import OAuthProvider, OtpPurpose


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
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str = "merchant"
    account_type: str = "merchant"
    user_id: str | None = None
    merchant_id: str | None = None
    business_name: str | None = None


class RefreshRequest(APIModel):
    refresh_token: str = Field(min_length=32, max_length=512)
    device_name: str | None = Field(default=None, max_length=120)


class LogoutRequest(APIModel):
    refresh_token: str | None = Field(default=None, min_length=32, max_length=512)


class OtpRequest(APIModel):
    identifier: str = Field(min_length=10, max_length=30)
    purpose: OtpPurpose = OtpPurpose.LOGIN


class OtpVerifyRequest(APIModel):
    challenge_id: UUID
    otp: str = Field(pattern=r"^\d{6}$")
    device_name: str | None = Field(default=None, max_length=120)


class OtpResendRequest(APIModel):
    challenge_id: UUID


class OtpChallengeResponse(APIModel):
    challenge_id: UUID
    destination: str
    expires_at: datetime
    resend_available_at: datetime


class AuthResult(APIModel):
    registration_required: bool = False
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    registration_token: str | None = None
    email: EmailStr | None = None
    role: str = "merchant"
    account_type: str = "merchant"
    user_id: str | None = None
    merchant_id: str | None = None
    business_name: str | None = None


class AddressInput(APIModel):
    flat_shop: str = Field(default="", max_length=150)
    address_line1: str = Field(default="", max_length=200)
    address_line2: str | None = Field(default=None, max_length=200)
    area_locality: str = Field(default="", max_length=150)
    landmark: str | None = Field(default=None, max_length=150)
    city: str = Field(default="", max_length=100)
    district: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=100)
    pincode: str = Field(default="", max_length=20)
    country: str = Field(default="India", max_length=60)
    latitude: float | None = None
    longitude: float | None = None


class RegistrationRequest(APIModel):
    email: EmailStr
    role: str = Field(default="merchant")
    business_name: str = Field(min_length=2, max_length=200)
    store_name: str = Field(min_length=2, max_length=200)
    registration_token: str = Field(min_length=20)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    phone_number: str | None = Field(default=None, min_length=10, max_length=30)
    gstin: str | None = Field(default=None)
    pan: str | None = Field(default=None)
    category: str | None = Field(default=None, max_length=100)
    address: dict[str, Any] = Field(default_factory=dict)
    device_name: str | None = Field(default=None, max_length=120)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        norm = v.strip().lower()
        if norm not in {"merchant", "supplier", "owner"}:
            raise ValueError("Role must be 'merchant' or 'supplier'")
        return "merchant" if norm == "owner" else norm

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            v = v.strip().upper()
            if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", v):
                raise ValueError("Invalid GSTIN format. Example: 29AABCU9603R1ZM")
            return v
        return v

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            v = v.strip().upper()
            if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", v):
                raise ValueError("Invalid PAN format. Example: AABCU9603R")
            return v
        return v

    @model_validator(mode="after")
    def validate_password_strength(self) -> "RegistrationRequest":
        if self.password and not (
            any(char.islower() for char in self.password)
            and any(char.isupper() for char in self.password)
            and any(char.isdigit() for char in self.password)
        ):
            raise ValueError("Password must contain upper-case, lower-case, and numeric characters")
        return self


class UserMeResponse(APIModel):
    user_id: UUID
    merchant_id: UUID
    role: str
    account_type: str
    email: str
    business_name: str
    phone_number: str | None = None
    gstin: str | None = None
    pan: str | None = None
    is_email_verified: bool = False
    is_phone_verified: bool = False
    stores: list[dict[str, Any]] = Field(default_factory=list)



class OAuthExchangeRequest(APIModel):
    challenge_id: UUID
    state: str = Field(min_length=20, max_length=256)
    nonce: str = Field(min_length=20, max_length=256)
    id_token: str | None = Field(default=None, min_length=20, max_length=10000)
    code: str | None = Field(default=None, max_length=2048)
    redirect_uri: str | None = None
    device_name: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_token_or_code(self) -> "OAuthExchangeRequest":
        if not self.id_token and not self.code:
            raise ValueError("Either id_token or code must be provided")
        return self


class OAuthStartResponse(APIModel):
    challenge_id: UUID
    provider: OAuthProvider
    state: str
    nonce: str
    client_id: str
    expires_at: datetime


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
    category: str | None = None
    barcode: str | None = None
    brand: str | None = None
    description: str | None = None
    unit_price: Decimal | None = None
    purchase_price: Decimal | None = None
    selling_price: Decimal | None = None
    mrp: Decimal | None = None
    gst_rate: Decimal | None = None
    expiry_date: str | None = None
    batch_number: str | None = None


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
    safety_stock: float = Field(default=2, ge=0)
    required_quantity: float = Field(default=0, ge=0)
    target_price: float = Field(gt=0)
    max_price: float = Field(gt=0)
    delivery_deadline: datetime

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


class AgentChatMessage(APIModel):
    role: str = "user"
    content: str


class AgentChatRequest(APIModel):
    message: str
    conversation_history: list[AgentChatMessage] = Field(default_factory=list)


class AgentChatResponse(APIModel):
    reply: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    business_context: dict[str, Any] = Field(default_factory=dict)


class LowStockReplenishmentResponse(APIModel):
    detected_count: int
    low_stock_items: list[dict[str, Any]]
    triggered_workflows: list[dict[str, Any]]
    notifications_sent: list[str]
