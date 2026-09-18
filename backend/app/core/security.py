import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.errors import AuthenticationError, StaleApprovalError

password_hash = PasswordHash.recommended()


def utc_now() -> datetime:
    return datetime.now(UTC)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def canonical_order_hash(proposal: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(proposal)).hexdigest()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def create_access_token(
    *, subject: UUID | str, merchant_id: UUID | str, secret: str, algorithm: str, ttl_minutes: int
) -> str:
    now = utc_now()
    claims = {
        "sub": str(subject),
        "merchant_id": str(merchant_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(claims, secret, algorithm=algorithm)


def create_approval_token(
    *,
    merchant_id: UUID | str,
    proposal_id: UUID | str,
    approval_id: UUID | str,
    order_hash: str,
    nonce: str,
    secret: str,
    algorithm: str = "HS256",
    ttl_minutes: int = 10,
    expires_at: datetime | None = None,
) -> str:
    now = utc_now()
    claims = {
        "sub": str(merchant_id),
        "proposal_id": str(proposal_id),
        "approval_id": str(approval_id),
        "order_hash": order_hash,
        "nonce": nonce,
        "type": "approval",
        "iat": now,
        "exp": expires_at or now + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(claims, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str = "HS256") -> dict[str, Any]:
    try:
        return jwt.decode(
            token, secret, algorithms=[algorithm], options={"require": ["exp", "iat"]}
        )
    except jwt.ExpiredSignatureError as exc:
        raise StaleApprovalError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid signed token") from exc


def sign_bytes(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    return hmac.compare_digest(sign_bytes(payload, secret), signature)
