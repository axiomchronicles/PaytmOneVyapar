from datetime import UTC, datetime

from app.a2a.schemas import A2AEnvelope
from app.core.errors import InvalidSignatureError
from app.core.security import canonical_json, sign_bytes, verify_signature


def sign_envelope(envelope: A2AEnvelope, secret: str) -> str:
    return sign_bytes(canonical_json(envelope.signing_document()), secret)


def verify_envelope(
    envelope: A2AEnvelope,
    *,
    secret: str,
    expected_receiver_id: str | None = None,
    max_clock_skew_seconds: int = 300,
    now: datetime | None = None,
) -> None:
    current = now or datetime.now(UTC)
    if not verify_signature(
        canonical_json(envelope.signing_document()), envelope.signature, secret
    ):
        raise InvalidSignatureError("A2A signature is invalid")
    if expected_receiver_id and str(envelope.receiver_agent_id) != expected_receiver_id:
        raise InvalidSignatureError("A2A receiver does not match this agent")
    if envelope.expires_at <= current:
        raise InvalidSignatureError("A2A message has expired")
    if abs((current - envelope.timestamp).total_seconds()) > max_clock_skew_seconds:
        raise InvalidSignatureError("A2A timestamp is outside the allowed clock skew")
