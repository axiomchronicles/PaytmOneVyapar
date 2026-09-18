from uuid import UUID

from pydantic import BaseModel


class RejectPurchase(BaseModel):
    approval_id: UUID
    merchant_id: UUID
    user_id: UUID
