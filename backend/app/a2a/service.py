from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.a2a.registry import AgentRegistry
from app.a2a.schemas import A2AEnvelope, A2APayload
from app.a2a.signing import verify_envelope
from app.core.errors import DuplicateEventError


class A2AMessageRepository(Protocol):
    async def nonce_seen(self, sender_id: UUID, nonce: str) -> bool: ...

    async def idempotency_seen(self, key: str) -> bool: ...

    async def save(self, envelope: A2AEnvelope, direction: str) -> None: ...


class A2AService:
    def __init__(
        self,
        *,
        registry: AgentRegistry,
        repository: A2AMessageRepository,
        receiver_id: str,
        max_clock_skew_seconds: int = 300,
    ) -> None:
        self.registry = registry
        self.repository = repository
        self.receiver_id = receiver_id
        self.max_clock_skew_seconds = max_clock_skew_seconds

    async def receive(self, envelope: A2AEnvelope) -> A2APayload:
        sender = self.registry.authorize_intent(envelope.sender_agent_id, envelope.intent)
        verify_envelope(
            envelope,
            secret=sender.signing_secret,
            expected_receiver_id=self.receiver_id,
            max_clock_skew_seconds=self.max_clock_skew_seconds,
            now=datetime.now(UTC),
        )
        if await self.repository.nonce_seen(envelope.sender_agent_id, envelope.nonce):
            raise DuplicateEventError("A2A nonce has already been used")
        if await self.repository.idempotency_seen(envelope.idempotency_key):
            raise DuplicateEventError("A2A message has already been processed")
        await self.repository.save(envelope, "INBOUND")
        return envelope.typed_payload()
