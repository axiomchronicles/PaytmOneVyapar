from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.a2a.schemas import A2AEnvelope, A2AIntent, PurchaseRequestPayload
from app.a2a.signing import sign_envelope, verify_envelope
from app.core.errors import InvalidSignatureError
from app.core.security import utc_now


def envelope() -> A2AEnvelope:
    now = utc_now()
    payload = PurchaseRequestPayload(
        merchant_id=uuid4(),
        store_id=uuid4(),
        sku="COLA",
        quantity="4",
        unit="crate",
        target_price="400",
        max_price="450",
        delivery_deadline=now + timedelta(days=2),
    )
    unsigned = A2AEnvelope(
        message_id=uuid4(),
        correlation_id=uuid4(),
        trace_id="trace",
        sender_agent_id=uuid4(),
        receiver_agent_id=uuid4(),
        intent=A2AIntent.PURCHASE_REQUEST,
        timestamp=now,
        expires_at=now + timedelta(minutes=5),
        nonce="nonce-with-16-chars",
        payload=payload.model_dump(mode="json", exclude={"intent"}),
        signature="0" * 64,
        idempotency_key="purchase-123",
    )
    return unsigned.model_copy(update={"signature": sign_envelope(unsigned, "shared-secret")})


def test_a2a_signature_and_typed_payload() -> None:
    message = envelope()
    verify_envelope(
        message, secret="shared-secret", expected_receiver_id=str(message.receiver_agent_id)
    )
    assert message.typed_payload().quantity == 4


def test_tampered_a2a_payload_is_rejected() -> None:
    message = envelope().model_copy(update={"payload": {**envelope().payload, "quantity": "99"}})
    with pytest.raises(InvalidSignatureError):
        verify_envelope(message, secret="shared-secret")


def test_a2a_schema_rejects_invalid_price_bounds() -> None:
    with pytest.raises(ValidationError):
        PurchaseRequestPayload(
            merchant_id=uuid4(),
            store_id=uuid4(),
            sku="COLA",
            quantity=1,
            unit="crate",
            target_price=500,
            max_price=450,
            delivery_deadline=utc_now() + timedelta(days=1),
        )
