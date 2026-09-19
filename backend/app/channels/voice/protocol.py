from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class VoiceEventType(StrEnum):
    SESSION_STARTED = "SESSION_STARTED"
    TRANSCRIPT_PARTIAL = "TRANSCRIPT_PARTIAL"
    TRANSCRIPT_FINAL = "TRANSCRIPT_FINAL"
    ACTION = "ACTION"
    RESPONSE_TEXT = "RESPONSE_TEXT"
    AUDIO_START = "AUDIO_START"
    AUDIO = "AUDIO"
    AUDIO_END = "AUDIO_END"
    ERROR = "ERROR"
    SESSION_ENDED = "SESSION_ENDED"


class VoiceEvent(BaseModel):
    type: VoiceEventType
    text: str | None = None
    language_code: str | None = None
    audio: bytes | None = None
    audio_content_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceIntentType(StrEnum):
    REPORT_LOW_STOCK = "REPORT_LOW_STOCK"
    REQUEST_PURCHASE = "REQUEST_PURCHASE"
    APPROVE_ACTIVE_PROPOSAL = "APPROVE_ACTIVE_PROPOSAL"
    MODIFY_ACTIVE_PROPOSAL = "MODIFY_ACTIVE_PROPOSAL"
    REJECT_ACTIVE_PROPOSAL = "REJECT_ACTIVE_PROPOSAL"
    GREETING = "GREETING"
    QUERY_INVENTORY = "QUERY_INVENTORY"
    QUERY_PROPOSALS = "QUERY_PROPOSALS"
    CAPABILITIES = "CAPABILITIES"
    GENERAL_QUERY = "GENERAL_QUERY"
    UNKNOWN = "UNKNOWN"


class VoiceIntent(BaseModel):
    intent: VoiceIntentType
    quantity: int | None = Field(default=None, gt=0)
    unit: str | None = None
    sku_hint: str | None = None
    explicit_confirmation: bool = False
    raw_text: str


class VoiceClientControl(BaseModel):
    type: Literal["end", "interrupt", "ping"]
