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
    speaking: bool = False
    reconnect_count: int = 0
    history: list[dict[str, str]] = field(default_factory=list)

    def add_user_message(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def add_assistant_message(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def interrupt(self) -> None:
        self.interrupted = True
        self.speaking = False

    def close(self) -> None:
        self.closed = True

    def reconnect(self) -> None:
        self.closed = False
        self.interrupted = False
        self.speaking = False
        self.reconnect_count += 1
