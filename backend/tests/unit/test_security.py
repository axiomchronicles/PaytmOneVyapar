from uuid import uuid4

import pytest

from app.core.errors import AuthenticationError, StaleApprovalError
from app.core.security import (
    canonical_order_hash,
    create_approval_token,
    decode_token,
)


def test_order_hash_is_canonical_and_changes_with_quantity() -> None:
    first = {"sku": "COLA", "quantity": "3", "unit_price": "10.00"}
    reordered = {"unit_price": "10.00", "quantity": "3", "sku": "COLA"}
    modified = {**first, "quantity": "2"}
    assert canonical_order_hash(first) == canonical_order_hash(reordered)
    assert canonical_order_hash(first) != canonical_order_hash(modified)


def test_approval_token_round_trip_and_tamper_detection() -> None:
    merchant_id, proposal_id, approval_id = uuid4(), uuid4(), uuid4()
    token = create_approval_token(
        merchant_id=merchant_id,
        proposal_id=proposal_id,
        approval_id=approval_id,
        order_hash="a" * 64,
        nonce="nonce-with-enough-entropy",
        secret="secret-that-is-long-enough-for-tests",
    )
    claims = decode_token(token, secret="secret-that-is-long-enough-for-tests")
    assert claims["approval_id"] == str(approval_id)
    with pytest.raises(AuthenticationError):
        decode_token(token + "x", secret="secret-that-is-long-enough-for-tests")


def test_expired_approval_token_is_rejected() -> None:
    token = create_approval_token(
        merchant_id=uuid4(),
        proposal_id=uuid4(),
        approval_id=uuid4(),
        order_hash="b" * 64,
        nonce="nonce-with-enough-entropy",
        secret="secret-that-is-long-enough-for-tests",
        ttl_minutes=-1,
    )
    with pytest.raises(StaleApprovalError):
        decode_token(token, secret="secret-that-is-long-enough-for-tests")
