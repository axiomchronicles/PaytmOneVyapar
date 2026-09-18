from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events import DomainEvent, EventType
from app.infrastructure.db.models import OutboxEvent


class OutboxPublisher:
    def __init__(self, session: AsyncSession, event_bus) -> None:
        self.session = session
        self.event_bus = event_bus

    async def publish_batch(self, *, limit: int = 100) -> int:
        rows = list(
            await self.session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.published_at.is_(None))
                .order_by(OutboxEvent.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        published = 0
        for row in rows:
            try:
                await self.event_bus.publish(
                    DomainEvent(
                        event_id=row.id,
                        event_type=EventType(row.event_type),
                        aggregate_type=row.aggregate_type,
                        aggregate_id=row.aggregate_id,
                        data=row.payload,
                        trace_id=row.trace_id,
                    )
                )
            except Exception as exc:
                row.attempts += 1
                row.last_error = type(exc).__name__
            else:
                row.published_at = datetime.now(UTC)
                published += 1
        await self.session.flush()
        return published
