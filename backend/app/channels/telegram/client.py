from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.contracts import TelegramProvider
from app.infrastructure.db.models import ChannelMessage


class TelegramChannel:
    """Channel adapter for communicating with merchants via Telegram Bot."""

    def __init__(self, provider: TelegramProvider, session: AsyncSession) -> None:
        self.provider = provider
        self.session = session

    async def send_approval(
        self,
        *,
        merchant_id: UUID,
        recipient: str,
        proposal: dict,
        idempotency_key: str,
    ) -> str:
        """Persist an outbound approval interaction in ChannelMessage and dispatch via Telegram Bot."""
        row = ChannelMessage(
            merchant_id=merchant_id,
            channel="TELEGRAM",
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

    async def send_text(
        self,
        *,
        merchant_id: UUID,
        recipient: str,
        body: str,
        idempotency_key: str,
    ) -> str:
        """Persist an outbound text notification in ChannelMessage and dispatch via Telegram Bot."""
        row = ChannelMessage(
            merchant_id=merchant_id,
            channel="TELEGRAM",
            direction="OUTBOUND",
            provider_message_id=f"pending:{idempotency_key}",
            idempotency_key=idempotency_key,
            message_type="text",
            payload={"recipient": recipient, "body": body},
            status="SENDING",
        )
        self.session.add(row)
        await self.session.flush()
        try:
            provider_id = await self.provider.send_text(
                recipient, body, idempotency_key=idempotency_key
            )
        except Exception:
            row.status = "FAILED"
            await self.session.flush()
            raise
        row.provider_message_id = provider_id
        row.status = "SENT"
        await self.session.flush()
        return provider_id


__all__ = ["TelegramChannel"]
