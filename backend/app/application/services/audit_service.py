from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import AuditLog


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        action: str,
        actor_type: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        merchant_id: UUID | None = None,
        trace_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                action=action,
                actor_type=actor_type,
                actor_id=actor_id,
                resource_type=resource_type,
                resource_id=resource_id,
                merchant_id=merchant_id,
                trace_id=trace_id,
                metadata_=metadata or {},
            )
        )
        await self.session.flush()
