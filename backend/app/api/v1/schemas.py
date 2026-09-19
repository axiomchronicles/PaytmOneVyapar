from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

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


class RegistrationRequest(APIModel):
    email: EmailStr
    business_name: str = Field(min_length=2, max_length=200)
    store_name: str = Field(min_length=2, max_length=200)
    registration_token: str = Field(min_length=20)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    phone_number: str | None = Field(default=None, min_length=10, max_length=30)
    address: dict[str, Any] = Field(default_factory=dict)
    device_name: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_password_strength(self) -> "RegistrationRequest":
        if self.password and not (
            any(char.islower() for char in self.password)
            and any(char.isupper() for char in self.password)
            and any(char.isdigit() for char in self.password)
        ):
            raise ValueError("Password must contain upper-case, lower-case, and numeric characters")
        return self


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
