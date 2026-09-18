from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.a2a.schemas import A2AEnvelope
from app.infrastructure.db.models import A2AMessage


class SQLA2AMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def nonce_seen(self, sender_id: UUID, nonce: str) -> bool:
        query = select(
            exists().where(A2AMessage.sender_agent_id == sender_id, A2AMessage.nonce == nonce)
        )
        return bool(await self.session.scalar(query))

    async def idempotency_seen(self, key: str) -> bool:
        return bool(
            await self.session.scalar(select(exists().where(A2AMessage.idempotency_key == key)))
        )

    async def save(self, envelope: A2AEnvelope, direction: str) -> None:
        self.session.add(
            A2AMessage(
                message_id=envelope.message_id,
                correlation_id=envelope.correlation_id,
                trace_id=envelope.trace_id,
                sender_agent_id=envelope.sender_agent_id,
                receiver_agent_id=envelope.receiver_agent_id,
                intent=envelope.intent,
                direction=direction,
                nonce=envelope.nonce,
                idempotency_key=envelope.idempotency_key,
                envelope=envelope.model_dump(mode="json"),
                expires_at=envelope.expires_at,
            )
        )
        await self.session.flush()
