from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.contracts import WhatsAppProvider
from app.infrastructure.db.models import ChannelMessage


class WhatsAppChannel:
    def __init__(self, provider: WhatsAppProvider, session: AsyncSession) -> None:
        self.provider = provider
        self.session = session

    async def send_approval(
        self, *, merchant_id: UUID, recipient: str, proposal: dict, idempotency_key: str
    ) -> str:
        row = ChannelMessage(
            merchant_id=merchant_id,
            channel="WHATSAPP",
            direction="OUTBOUND",
            provider_message_id=f"pending:{idempotency_key}",
            idempotency_key=idempotency_key,
            message_type="interactive_approval",
            payload=proposal,
            status="SENDING",
        )
        self.session.add(row)
        await self.session.flush()
        try:
            provider_id = await self.provider.send_approval(
                recipient, proposal, idempotency_key=idempotency_key
            )
        except Exception:
            row.status = "FAILED"
            await self.session.flush()
            raise
        row.provider_message_id = provider_id
        row.status = "SENT"
        await self.session.flush()
        return provider_id


__all__ = ["WhatsAppChannel"]
