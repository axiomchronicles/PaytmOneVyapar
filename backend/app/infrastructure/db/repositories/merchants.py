from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.infrastructure.db.models import Merchant, Store, User


class MerchantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, merchant_id: UUID) -> Merchant:
        merchant = await self.session.get(Merchant, merchant_id)
        if merchant is None:
            raise NotFoundError("Merchant not found")
        return merchant

    async def user_by_email(self, email: str) -> User | None:
        return await self.session.scalar(
            select(User).where(func.lower(User.email) == email.lower())
        )

    async def stores(self, merchant_id: UUID) -> list[Store]:
        result = await self.session.scalars(select(Store).where(Store.merchant_id == merchant_id))
        return list(result)
