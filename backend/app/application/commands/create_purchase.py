from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CreatePurchase(BaseModel):
    merchant_id: UUID
    store_id: UUID
    sku: str
    quantity: Decimal = Field(gt=0)
    unit: str
    target_price: Decimal = Field(gt=0)
    max_price: Decimal = Field(gt=0)
    delivery_deadline: datetime
    request_id: str
