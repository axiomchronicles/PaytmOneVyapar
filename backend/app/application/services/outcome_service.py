from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events import DomainEvent
from app.infrastructure.db.models import OutboxEvent


class OutcomeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(self, event: DomainEvent) -> UUID:
        row = OutboxEvent(
            id=event.event_id,
            merchant_id=event.merchant_id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=event.data,
            trace_id=event.trace_id,
            correlation_id=event.correlation_id,
            event_version=event.version,
        )
        self.session.add(row)
        await self.session.flush()
        return row.id
