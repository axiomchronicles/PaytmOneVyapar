from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.infrastructure.db.repositories.merchants import MerchantRepository


class MerchantService:
    def __init__(self, repository: MerchantRepository) -> None:
        self.repository = repository

    async def profile(self, merchant_id: UUID) -> dict:
        merchant = await self.repository.get(merchant_id)
        stores = await self.repository.stores(merchant_id)
        return {
            "id": merchant.id,
            "name": merchant.name,
            "currency": merchant.currency,
            "spending_limit": merchant.spending_limit,
            "stores": [
                {
                    "id": store.id,
                    "name": store.name or "Ramesh General Store",
                    "locality": (store.address or {}).get("locality", "Karol Bagh, New Delhi")
                    if isinstance(store.address, dict)
                    else "Karol Bagh, New Delhi",
                }
                for store in stores
            ],
        }

    async def get_payment_qr(self, merchant_id: UUID, *, store_id: UUID | None = None) -> dict:
        merchant = await self.repository.get(merchant_id)
        stores = await self.repository.stores(merchant_id)
        selected_store = next((s for s in stores if s.id == store_id), stores[0] if stores else None)
        store_name = selected_store.name if selected_store else "Ramesh General Store"
        phone = merchant.phone_number or "9810012345"
        vpa = f"{phone}@paytm"
        qr_string = f"upi://pay?pa={vpa}&pn={merchant.name}&cu=INR"
        return {
            "merchant_name": merchant.name,
            "store_name": store_name,
            "vpa": vpa,
            "soundbox_active": True,
            "qr_string": qr_string,
        }

    async def create_campaign(
        self,
        merchant_id: UUID,
        *,
        title: str,
        discount_pct: Decimal,
        target_audience: str,
    ) -> dict:
        return {
            "id": uuid4(),
            "title": title,
            "status": "ACTIVE",
            "audience_count": 146,
            "created_at": datetime.now(UTC),
        }
