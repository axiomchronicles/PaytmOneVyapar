from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.approval_service import ApprovalService
from app.channels.whatsapp.approval_handler import (
    WhatsAppApprovalAction,
    parse_approval_callback,
)
from app.channels.whatsapp.webhook import parse_webhook
from app.core.config import Settings, get_settings
from app.domain.enums import ApprovalStatus
from app.infrastructure.db.models import ChannelMessage, Merchant, User
from app.infrastructure.db.repositories.approvals import ApprovalRepository
from app.infrastructure.db.session import get_session
from app.integrations.whatsapp.meta import verify_webhook_signature

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])
"""Meta WhatsApp Cloud API webhook endpoint (Coming Soon).

The WhatsApp channel is currently in preview/coming-soon status.
The active production-ready channel for merchant approvals is Telegram (@PaytmOneVyapar_bot).
"""


@router.get("")
async def verify(
    response: Response,
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
) -> Response:
    """WhatsApp webhook challenge verification (Channel Status: Coming Soon)."""
    response.headers["X-Channel-Status"] = "coming_soon"
    if mode is None:
        return Response(
            content='{"channel":"WHATSAPP","status":"coming_soon","message":"WhatsApp integration is coming soon. Active interactive channel is Telegram (@PaytmOneVyapar_bot)."}',
            media_type="application/json",
            headers={"X-Channel-Status": "coming_soon"},
        )
    expected = settings.whatsapp_verify_token
    if mode == "subscribe" and expected and verify_token == expected.get_secret_value():
        return Response(
            content=challenge or "",
            media_type="text/plain",
            headers={"X-Channel-Status": "coming_soon"},
        )
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("")
async def webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    secret = settings.whatsapp_app_secret
    if secret is None:
        raise HTTPException(status_code=503, detail="WhatsApp webhook is not configured")
    raw = await request.body()
    if not verify_webhook_signature(raw, x_hub_signature_256, secret.get_secret_value()):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    messages = parse_webhook(await request.json())
    accepted = 0
    for message in messages:
        session.add(
            ChannelMessage(
                channel="WHATSAPP",
                direction="INBOUND",
                provider_message_id=message.message_id,
                message_type=message.kind,
                payload={
                    "sender": message.sender,
                    "text": message.text,
                    "reply_id": message.reply_id,
                },
                status="RECEIVED",
            )
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        else:
            accepted += 1
            if message.reply_id:
                if not message.reply_id.startswith("approval:"):
                    continue
                try:
                    callback = parse_approval_callback(message.reply_id)
                except ValueError:
                    continue
                merchant = await session.scalar(
                    select(Merchant).where(Merchant.phone_number == message.sender)
                )
                if merchant is None:
                    continue
                user = await session.scalar(
                    select(User).where(
                        User.merchant_id == merchant.id,
                        User.is_active.is_(True),
                    )
                )
                if user is None:
                    continue
                repository = ApprovalRepository(session)
                approval = await repository.get(callback.approval_id)
                service = ApprovalService(
                    repository,
                    secret=settings.auth_approval_secret.get_secret_value(),
                    algorithm=settings.auth_jwt_algorithm,
                    ttl_minutes=settings.auth_approval_token_minutes,
                )
                if callback.action == WhatsAppApprovalAction.MODIFY:
                    stored = await session.scalar(
                        select(ChannelMessage).where(
                            ChannelMessage.provider_message_id == message.message_id
                        )
                    )
                    if stored:
                        stored.status = "NEEDS_MODIFICATION_DETAILS"
                        await session.commit()
                    continue
                if approval.workflow_request_id:
                    await request.app.state.workflow_runtime.resume(
                        merchant_id=merchant.id,
                        request_id=approval.workflow_request_id,
                        action=(
                            ApprovalStatus.APPROVED
                            if callback.action == WhatsAppApprovalAction.APPROVE
                            else ApprovalStatus.REJECTED
                        ),
                        approval_token=service.token_for(approval, merchant_id=merchant.id),
                        user_id=user.id,
                        expected_approval_id=approval.id,
                    )
                elif callback.action == WhatsAppApprovalAction.APPROVE:
                    await service.approve(
                        approval.id,
                        merchant_id=merchant.id,
                        user_id=user.id,
                        token=service.token_for(approval, merchant_id=merchant.id),
                    )
                    await session.commit()
                else:
                    await service.reject(approval.id, merchant_id=merchant.id, user_id=user.id)
                    await session.commit()
    return {
        "received": accepted,
        "status": "coming_soon",
        "channel": "WHATSAPP",
        "message": "WhatsApp channel is in preview (Coming Soon). Active interactive channel is Telegram (@PaytmOneVyapar_bot).",
    }
