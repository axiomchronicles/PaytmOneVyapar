from uuid import UUID

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
            "stores": [{"id": store.id, "name": store.name} for store in stores],
        }
