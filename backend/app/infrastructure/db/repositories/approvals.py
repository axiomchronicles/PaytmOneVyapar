from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.infrastructure.db.models import Approval


class ApprovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self,
        approval_id: UUID,
        *,
        merchant_id: UUID | None = None,
        for_update: bool = False,
    ) -> Approval:
        # Older mobile builds used the proposal UUID in approval deep links.
        # Both identifiers are tenant-scoped and indexed, so resolve either
        # identifier while every approval action still verifies its signed token.
        query = select(Approval).where(
            or_(Approval.id == approval_id, Approval.proposal_id == approval_id)
        )
        if merchant_id is not None:
            query = query.where(Approval.merchant_id == merchant_id)
        if for_update:
            query = query.with_for_update()
        approval = await self.session.scalar(query)
        if approval is None:
            raise NotFoundError("Approval not found")
        return approval

    async def list(
        self,
        merchant_id: UUID,
        *,
        status: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        cursor: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[Approval]:
        query = select(Approval).where(Approval.merchant_id == merchant_id)
        if status:
            query = query.where(Approval.status == status)
        if created_from:
            query = query.where(Approval.created_at >= created_from)
        if created_to:
            query = query.where(Approval.created_at < created_to)
        if cursor:
            created_at, row_id = cursor
            query = query.where(
                or_(
                    Approval.created_at < created_at,
                    and_(Approval.created_at == created_at, Approval.id < row_id),
                )
            )
        return list(
            await self.session.scalars(
                query.order_by(Approval.created_at.desc(), Approval.id.desc()).limit(limit + 1)
            )
        )

    async def add(self, approval: Approval) -> Approval:
        self.session.add(approval)
        await self.session.flush()
        return approval
