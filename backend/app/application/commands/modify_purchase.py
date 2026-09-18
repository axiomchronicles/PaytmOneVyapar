from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ModifyPurchase(BaseModel):
    approval_id: UUID
    merchant_id: UUID
    user_id: UUID
    quantity: Decimal | None = Field(default=None, gt=0)
    max_unit_price: Decimal | None = Field(default=None, gt=0)
