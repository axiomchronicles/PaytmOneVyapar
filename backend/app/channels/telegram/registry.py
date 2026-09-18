from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger()

# In-memory fast stores (fallback and primary cache)
_PHONE_TO_CHAT: dict[str, str] = {}
_ACTIVE_OTPS: dict[str, tuple[str, datetime]] = {}


def clean_phone_digits(phone: str) -> str:
    """Extract standard digits for indexing."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return f"91{digits}"
    return digits


def register_phone_telegram(phone: str, chat_id: str | int, username: str | None = None) -> None:
    """Register mapping between phone number and Telegram chat_id."""
    clean = clean_phone_digits(phone)
    cid = str(chat_id)
    _PHONE_TO_CHAT[clean] = cid
    if clean.startswith("91") and len(clean) == 12:
        _PHONE_TO_CHAT[clean[2:]] = cid
        _PHONE_TO_CHAT[f"+{clean}"] = cid
    logger.info(
        "telegram_phone_registered", phone=phone, clean=clean, chat_id=cid, username=username
    )


def get_telegram_chat_for_phone(phone: str) -> str | None:
    """Lookup telegram chat_id by phone number."""
    clean = clean_phone_digits(phone)
    if clean in _PHONE_TO_CHAT:
        return _PHONE_TO_CHAT[clean]
    if clean.startswith("91") and len(clean) == 12:
        raw10 = clean[2:]
        if raw10 in _PHONE_TO_CHAT:
            return _PHONE_TO_CHAT[raw10]
    return None


def store_active_otp(identifier: str, otp: str, ttl_minutes: int = 5) -> None:
    """Store plaintext active OTP for quick delivery/retrieval in Telegram."""
    clean = clean_phone_digits(identifier)
    expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
    _ACTIVE_OTPS[clean] = (otp, expires_at)
    if clean.startswith("91") and len(clean) == 12:
        _ACTIVE_OTPS[clean[2:]] = (otp, expires_at)


def get_active_otp(identifier: str) -> str | None:
    """Retrieve active unexpired OTP for identifier."""
    clean = clean_phone_digits(identifier)
    item = _ACTIVE_OTPS.get(clean)
    if not item and clean.startswith("91") and len(clean) == 12:
        item = _ACTIVE_OTPS.get(clean[2:])
    if item:
        otp, expires_at = item
        if datetime.now(UTC) < expires_at:
            return otp
        _ACTIVE_OTPS.pop(clean, None)
    return None
