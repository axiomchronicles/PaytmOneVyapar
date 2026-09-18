from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class TelegramApprovalAction(StrEnum):
    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    REJECT = "REJECT"


class TelegramApprovalCallback(BaseModel):
    approval_id: UUID
    action: TelegramApprovalAction


def parse_approval_callback(callback_data: str) -> TelegramApprovalCallback:
    """Parse callback data in format 'approval:{approval_id}:{action}'."""
    parts = callback_data.split(":")
    if len(parts) != 3 or parts[0] != "approval":
        raise ValueError(f"Invalid Telegram approval callback format: {callback_data}")
    return TelegramApprovalCallback(
        approval_id=UUID(parts[1]), action=TelegramApprovalAction(parts[2])
    )
