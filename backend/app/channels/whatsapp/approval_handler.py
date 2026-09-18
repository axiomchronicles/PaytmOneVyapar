from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class WhatsAppApprovalAction(StrEnum):
    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    REJECT = "REJECT"


class WhatsAppApprovalCallback(BaseModel):
    approval_id: UUID
    action: WhatsAppApprovalAction


def parse_approval_callback(reply_id: str) -> WhatsAppApprovalCallback:
    parts = reply_id.split(":")
    if len(parts) != 3 or parts[0] != "approval":
        raise ValueError("Unknown WhatsApp interaction")
    return WhatsAppApprovalCallback(approval_id=parts[1], action=parts[2])
