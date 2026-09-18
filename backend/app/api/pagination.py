import base64
import json
from datetime import datetime
from uuid import UUID

from app.core.errors import InvalidRequestError


def encode_cursor(created_at: datetime, row_id: UUID) -> str:
    raw = json.dumps([created_at.isoformat(), str(row_id)], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> tuple[datetime, UUID] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        created_at, row_id = json.loads(base64.urlsafe_b64decode(padded).decode())
        return datetime.fromisoformat(created_at), UUID(row_id)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise InvalidRequestError("Pagination cursor is invalid") from exc


def next_cursor(rows: list, limit: int) -> str | None:
    if len(rows) <= limit:
        return None
    last = rows[limit - 1]
    return encode_cursor(last.created_at, last.id)
