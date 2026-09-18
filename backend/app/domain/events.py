from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.security import utc_now


class EventType(StrEnum):
    INVENTORY_LOW = "INVENTORY_LOW"
    DEMAND_SURGE_DETECTED = "DEMAND_SURGE_DETECTED"
    PURCHASE_PROPOSAL_CREATED = "PURCHASE_PROPOSAL_CREATED"
    NEGOTIATION_STARTED = "NEGOTIATION_STARTED"
    QUOTE_RECEIVED = "QUOTE_RECEIVED"
    NEGOTIATION_COMPLETED = "NEGOTIATION_COMPLETED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    ORDER_EXECUTED = "ORDER_EXECUTED"
    ORDER_FAILED = "ORDER_FAILED"
    SUPPLIER_CONFIRMATION_RECEIVED = "SUPPLIER_CONFIRMATION_RECEIVED"
    VOICE_SESSION_STARTED = "VOICE_SESSION_STARTED"
    VOICE_TRANSCRIPT_FINAL = "VOICE_TRANSCRIPT_FINAL"
    A2A_MESSAGE_RECEIVED = "A2A_MESSAGE_RECEIVED"
    INVENTORY_UPDATED = "INVENTORY_UPDATED"
    NEGOTIATION_UPDATED = "NEGOTIATION_UPDATED"
    NOTIFICATION_CREATED = "NOTIFICATION_CREATED"


class DomainEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    aggregate_type: str
    aggregate_id: UUID
    merchant_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utc_now)
    correlation_id: str | None = None
    trace_id: str | None = None
    version: int = Field(default=1, ge=1)

    @property
    def data(self) -> dict[str, Any]:
        """Backward-compatible internal alias while the public envelope uses payload."""
        return self.payload
