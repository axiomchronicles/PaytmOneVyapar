from uuid import UUID

from pydantic import BaseModel, Field


class ApprovePurchase(BaseModel):
    approval_id: UUID
    merchant_id: UUID
    user_id: UUID
    approval_token: str = Field(min_length=20)
    idempotency_key: str = Field(min_length=8)
