from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.core.security import utc_now


@dataclass
class VoiceSession:
    merchant_id: UUID
    user_id: UUID
    language_code: str
    sample_rate: int = 16000
    encoding: str = "linear16"
    active_proposal_id: UUID | None = None
    active_request_id: str | None = None
    approval_token: str | None = None
    session_id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=utc_now)
    interrupted: bool = False
    closed: bool = False
    reconnect_count: int = 0

    def interrupt(self) -> None:
        self.interrupted = True

    def close(self) -> None:
        self.closed = True

    def reconnect(self) -> None:
        self.closed = False
        self.interrupted = False
        self.reconnect_count += 1
