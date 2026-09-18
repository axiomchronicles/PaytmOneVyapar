from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator


class A2AIntent(StrEnum):
    INVENTORY_SHORTAGE_ALERT = "INVENTORY_SHORTAGE_ALERT"
    PURCHASE_REQUEST = "PURCHASE_REQUEST"
    QUOTE = "QUOTE"
    COUNTER_OFFER = "COUNTER_OFFER"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    OFFER_REJECTED = "OFFER_REJECTED"
    DELIVERY_CONFIRMATION = "DELIVERY_CONFIRMATION"
    ORDER_CONFIRMATION = "ORDER_CONFIRMATION"
    CANCELLATION = "CANCELLATION"


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InventoryShortagePayload(Payload):
    intent: Literal[A2AIntent.INVENTORY_SHORTAGE_ALERT] = A2AIntent.INVENTORY_SHORTAGE_ALERT
    merchant_id: UUID
    store_id: UUID
    sku: str
    available_quantity: Decimal = Field(ge=0)
    required_quantity: Decimal = Field(gt=0)
    unit: str


class PurchaseRequestPayload(Payload):
    intent: Literal[A2AIntent.PURCHASE_REQUEST] = A2AIntent.PURCHASE_REQUEST
    merchant_id: UUID
    store_id: UUID
    sku: str
    quantity: Decimal = Field(gt=0)
    unit: str
    target_price: Decimal = Field(gt=0)
    max_price: Decimal = Field(gt=0)
    delivery_deadline: datetime

    @model_validator(mode="after")
    def check_price_limit(self) -> "PurchaseRequestPayload":
        if self.target_price > self.max_price:
            raise ValueError("target_price cannot exceed max_price")
        return self


class QuotePayload(Payload):
    intent: Literal[A2AIntent.QUOTE] = A2AIntent.QUOTE
    quote_id: str
    sku: str
    available_quantity: Decimal = Field(ge=0)
    unit_price: Decimal = Field(gt=0)
    currency: str = "INR"
    delivery_at: datetime
    expires_at: datetime


class CounterOfferPayload(Payload):
    intent: Literal[A2AIntent.COUNTER_OFFER] = A2AIntent.COUNTER_OFFER
    quote_id: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    round: int = Field(ge=1, le=10)


class AcceptedProposalPayload(Payload):
    proposal_id: UUID
    merchant_id: UUID
    store_id: UUID
    supplier_id: UUID
    sku: str
    quantity: Decimal = Field(gt=0)
    unit: str
    unit_price: Decimal = Field(gt=0)
    currency: str
    delivery_at: datetime
    quote_id: str


class OfferDecisionPayload(Payload):
    intent: Literal[A2AIntent.OFFER_ACCEPTED, A2AIntent.OFFER_REJECTED]
    quote_id: str
    reason: str | None = None
    proposal: AcceptedProposalPayload | None = None

    @model_validator(mode="after")
    def accepted_offer_needs_proposal(self) -> "OfferDecisionPayload":
        if self.intent == A2AIntent.OFFER_ACCEPTED and self.proposal is None:
            raise ValueError("An accepted offer requires the canonical proposal")
        return self


class DeliveryConfirmationPayload(Payload):
    intent: Literal[A2AIntent.DELIVERY_CONFIRMATION] = A2AIntent.DELIVERY_CONFIRMATION
    order_id: UUID
    delivered_at: datetime
    quantity: Decimal = Field(gt=0)


class OrderConfirmationPayload(Payload):
    intent: Literal[A2AIntent.ORDER_CONFIRMATION] = A2AIntent.ORDER_CONFIRMATION
    order_id: UUID
    supplier_reference: str
    expected_delivery_at: datetime


class CancellationPayload(Payload):
    intent: Literal[A2AIntent.CANCELLATION] = A2AIntent.CANCELLATION
    order_id: UUID | None = None
    quote_id: str | None = None
    reason: str

    @model_validator(mode="after")
    def check_reference(self) -> "CancellationPayload":
        if not self.order_id and not self.quote_id:
            raise ValueError("order_id or quote_id is required")
        return self


A2APayload = Annotated[
    InventoryShortagePayload
    | PurchaseRequestPayload
    | QuotePayload
    | CounterOfferPayload
    | OfferDecisionPayload
    | DeliveryConfirmationPayload
    | OrderConfirmationPayload
    | CancellationPayload,
    Field(discriminator="intent"),
]

payload_adapter = TypeAdapter(A2APayload)


class A2AEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: Literal["vyapaar-a2a-v1"] = "vyapaar-a2a-v1"
    message_id: UUID
    correlation_id: UUID
    trace_id: str
    sender_agent_id: UUID
    receiver_agent_id: UUID
    intent: A2AIntent
    timestamp: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    payload: dict[str, Any]
    signature: str = Field(min_length=64, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("timestamp", "expires_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_payload(self) -> "A2AEnvelope":
        if self.expires_at <= self.timestamp:
            raise ValueError("expires_at must be after timestamp")
        if "intent" in self.payload:
            raise ValueError("payload must not override the envelope intent")
        document = {"intent": self.intent, **self.payload}
        payload_adapter.validate_python(document)
        return self

    def typed_payload(self) -> A2APayload:
        return payload_adapter.validate_python({"intent": self.intent, **self.payload})

    def signing_document(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"signature"})
