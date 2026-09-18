from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.infrastructure.db.models import Approval


class ApprovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, approval_id: UUID, *, for_update: bool = False) -> Approval:
        query = select(Approval).where(Approval.id == approval_id)
        if for_update:
            query = query.with_for_update()
        approval = await self.session.scalar(query)
        if approval is None:
            raise NotFoundError("Approval not found")
        return approval

    async def add(self, approval: Approval) -> Approval:
        self.session.add(approval)
        await self.session.flush()
        return approval
