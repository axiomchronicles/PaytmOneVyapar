import html
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.approval_service import ApprovalService
from app.channels.telegram.approval_handler import (
    TelegramApprovalAction,
    parse_approval_callback,
)
from app.channels.telegram.formatter import format_decision_confirmation
from app.channels.telegram.webhook import parse_telegram_webhook
from app.core.config import Settings, get_settings
from app.domain.enums import ApprovalStatus
from app.infrastructure.db.models import Approval, ChannelMessage, Merchant, User
from app.infrastructure.db.repositories.approvals import ApprovalRepository
from app.infrastructure.db.session import get_session
from app.integrations.telegram.client import TelegramBotProvider, verify_telegram_secret

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks/telegram", tags=["telegram"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_telegram_status(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Health and status check for Telegram bot channel."""
    configured = settings.telegram_bot_token is not None
    bot_info: dict[str, Any] = {}
    provider: TelegramBotProvider | None = getattr(request.app.state, "telegram_provider", None)
    if provider:
        try:
            me = await provider.get_me()
            bot_info = {
                "id": me.get("id"),
                "username": me.get("username"),
                "first_name": me.get("first_name"),
            }
        except Exception as exc:
            logger.warning("telegram_get_me_failed", error=str(exc))
            bot_info = {"error": str(exc)}

    return {
        "channel": "TELEGRAM",
        "status": "active" if configured else "unconfigured",
        "bot_username": settings.telegram_bot_username,
        "bot_url": f"https://t.me/{settings.telegram_bot_username}",
        "bot_info": bot_info,
    }


@router.post("")
async def telegram_webhook(
    request: Request,
    payload: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Handle incoming updates (commands, messages, callback queries) from Telegram."""
    if settings.telegram_bot_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot channel is not configured",
        )

    # Validate secret token if configured
    if settings.telegram_webhook_secret:
        expected = settings.telegram_webhook_secret.get_secret_value()
        if not verify_telegram_secret(x_telegram_bot_api_secret_token, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Telegram webhook secret token",
            )

    provider: TelegramBotProvider | None = getattr(request.app.state, "telegram_provider", None)
    inbound_items = parse_telegram_webhook(payload)
    accepted = 0

    for item in inbound_items:
        # Record inbound message for deduplication and audit trail
        channel_msg = ChannelMessage(
            channel="TELEGRAM",
            direction="INBOUND",
            provider_message_id=item.message_id,
            message_type=item.kind,
            payload={
                "chat_id": item.chat_id,
                "sender_id": item.sender_id,
                "sender_name": item.sender_name,
                "username": item.username,
                "text": item.text,
                "callback_data": item.callback_data,
            },
            status="RECEIVED",
        )
        session.add(channel_msg)
        try:
            await session.commit()
        except IntegrityError:
            # Already processed (deduplication)
            await session.rollback()
            continue

        accepted += 1

        # ---------------------------------------------------------
        # Case A: Interactive Button Click (Callback Query)
        # ---------------------------------------------------------
        if item.kind == "callback_query" and item.callback_data:
            if not item.callback_data.startswith("approval:"):
                if provider and item.callback_query_id:
                    await provider.answer_callback_query(item.callback_query_id)
                continue

            try:
                callback = parse_approval_callback(item.callback_data)
            except ValueError:
                if provider and item.callback_query_id:
                    await provider.answer_callback_query(
                        item.callback_query_id, text="Invalid approval action"
                    )
                continue

            # Answer callback query to dismiss UI loading state immediately
            if provider and item.callback_query_id:
                action_label = {
                    TelegramApprovalAction.APPROVE: "Approving order...",
                    TelegramApprovalAction.MODIFY: "Requesting modification...",
                    TelegramApprovalAction.REJECT: "Declining order...",
                }.get(callback.action, "Processing...")
                await provider.answer_callback_query(item.callback_query_id, text=action_label)

            # Retrieve approval record
            repository = ApprovalRepository(session)
            try:
                approval = await repository.get(callback.approval_id)
            except Exception:
                logger.warning(
                    "approval_not_found_for_telegram", approval_id=str(callback.approval_id)
                )
                continue

            merchant = await session.get(Merchant, approval.merchant_id)
            if merchant is None:
                continue

            # Auto-link telegram chat_id to merchant settings if not yet stored
            current_settings = dict(merchant.settings or {})
            if current_settings.get("telegram_chat_id") != item.chat_id:
                current_settings["telegram_chat_id"] = item.chat_id
                if item.username:
                    current_settings["telegram_username"] = item.username
                merchant.settings = current_settings
                channel_msg.merchant_id = merchant.id
                await session.commit()

            # Find active user for authorization audit
            user = await session.scalar(
                select(User).where(
                    User.merchant_id == merchant.id,
                    User.is_active.is_(True),
                )
            )
            if user is None:
                continue

            service = ApprovalService(
                repository,
                secret=settings.auth_approval_secret.get_secret_value(),
                algorithm=settings.auth_jwt_algorithm,
                ttl_minutes=settings.auth_approval_token_minutes,
            )

            # Handle Modify
            if callback.action == TelegramApprovalAction.MODIFY:
                stored = await session.scalar(
                    select(ChannelMessage).where(
                        ChannelMessage.channel == "TELEGRAM",
                        ChannelMessage.provider_message_id == item.message_id,
                    )
                )
                if stored:
                    stored.status = "NEEDS_MODIFICATION_DETAILS"
                    await session.commit()

                if provider:
                    raw_msg = item.raw.get("message", {})
                    orig_msg_id = raw_msg.get("message_id")
                    if orig_msg_id:
                        sku = approval.proposal_payload.get("sku", "item")
                        new_text = format_decision_confirmation(sku, "MODIFY")
                        await provider.edit_message_text(
                            item.chat_id,
                            orig_msg_id,
                            new_text,
                            reply_markup={"inline_keyboard": []},
                        )
                continue

            # Resume workflow or execute direct approval/rejection
            if approval.workflow_request_id and hasattr(request.app.state, "workflow_runtime"):
                await request.app.state.workflow_runtime.resume(
                    merchant_id=merchant.id,
                    request_id=approval.workflow_request_id,
                    action=(
                        ApprovalStatus.APPROVED
                        if callback.action == TelegramApprovalAction.APPROVE
                        else ApprovalStatus.REJECTED
                    ),
                    approval_token=service.token_for(approval, merchant_id=merchant.id),
                    user_id=user.id,
                    expected_approval_id=approval.id,
                )
            elif callback.action == TelegramApprovalAction.APPROVE:
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

            # Update original Telegram message to confirm decision and remove action buttons
            if provider:
                raw_msg = item.raw.get("message", {})
                orig_msg_id = raw_msg.get("message_id")
                if orig_msg_id:
                    sku = approval.proposal_payload.get("sku", "item")
                    total_amount = approval.proposal_payload.get("total_amount")
                    new_text = format_decision_confirmation(
                        sku,
                        callback.action.value,
                        total_amount=str(total_amount) if total_amount else None,
                    )
                    await provider.edit_message_text(
                        item.chat_id, orig_msg_id, new_text, reply_markup={"inline_keyboard": []}
                    )

        # ---------------------------------------------------------
        # Case B: Commands and Text Messages
        # ---------------------------------------------------------
        elif item.kind in {"command", "message"} and item.text and provider:
            text = item.text.strip()
            cmd = text.split()[0].lower() if text else ""

            if cmd == "/start":
                welcome = (
                    f"👋 <b>Welcome to Paytm ONE Vyapar!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"I am your autonomous <b>Vyapar Commander</b> bot.\n\n"
                    f"I monitor your inventory, forecast demand, negotiate with suppliers, "
                    f"and bring purchase proposals right here for your one-tap approval.\n\n"
                    f"🆔 <b>Your Telegram Chat ID:</b> <code>{item.chat_id}</code>\n\n"
                    f"<b>Quick Commands:</b>\n"
                    f"• <code>/connect &lt;phone&gt;</code> - Link your merchant account\n"
                    f"• <code>/status</code> - View pending purchase approvals\n"
                    f"• <code>/help</code> - Show commands and assistance"
                )
                await provider.send_text(item.chat_id, welcome)

            elif cmd == "/connect":
                parts = text.split(maxsplit=1)
                if len(parts) < 2:
                    await provider.send_text(
                        item.chat_id,
                        "ℹ️ Please supply your registered phone number or email:\n"
                        "Example: <code>/connect 9876543210</code> or <code>/connect merchant@example.com</code>",
                    )
                    continue

                identifier = parts[1].strip()
                # Lookup by phone or email
                merchant = None
                if "@" in identifier:
                    user = await session.scalar(
                        select(User).where(func.lower(User.email) == identifier.lower())
                    )
                    if user:
                        merchant = await session.get(Merchant, user.merchant_id)
                else:
                    clean_phone = "".join(c for c in identifier if c.isdigit() or c == "+")
                    # Try exact, without +91, or with +91
                    candidates = [clean_phone]
                    if clean_phone.startswith("+91"):
                        candidates.append(clean_phone[3:])
                    elif len(clean_phone) == 10:
                        candidates.append(f"+91{clean_phone}")

                    merchant = await session.scalar(
                        select(Merchant).where(Merchant.phone_number.in_(candidates))
                    )

                if merchant:
                    cur_settings = dict(merchant.settings or {})
                    cur_settings["telegram_chat_id"] = item.chat_id
                    if item.username:
                        cur_settings["telegram_username"] = item.username
                    merchant.settings = cur_settings
                    await session.commit()

                    await provider.send_text(
                        item.chat_id,
                        f"✅ <b>Merchant Account Linked!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"<b>Business:</b> {html.escape(merchant.name)}\n"
                        f"<b>Currency:</b> {merchant.currency}\n\n"
                        f"You will now receive replenishment recommendations and instant approval prompts here!",
                    )
                else:
                    await provider.send_text(
                        item.chat_id,
                        "❌ <b>Merchant Not Found</b>\n\n"
                        "We couldn't find a merchant account matching that identifier. "
                        "Please verify your registered number in the Vyapar app.",
                    )

            elif cmd == "/status":
                # Find merchant linked to this chat_id
                merchants = list(await session.scalars(select(Merchant)))
                linked = None
                for m in merchants:
                    if (m.settings or {}).get("telegram_chat_id") == item.chat_id:
                        linked = m
                        break

                if not linked:
                    await provider.send_text(
                        item.chat_id,
                        "ℹ️ Your Telegram account is not yet linked to a merchant.\n"
                        "Use <code>/connect &lt;phone&gt;</code> to link your account.",
                    )
                    continue

                # Find pending approvals
                pending_approvals = list(
                    await session.scalars(
                        select(Approval)
                        .where(
                            Approval.merchant_id == linked.id,
                            Approval.status == ApprovalStatus.PENDING,
                        )
                        .order_by(Approval.created_at.desc())
                        .limit(5)
                    )
                )

                if not pending_approvals:
                    await provider.send_text(
                        item.chat_id,
                        f"✅ <b>All caught up!</b>\n\n"
                        f"No pending approvals for <b>{html.escape(linked.name)}</b>.",
                    )
                else:
                    await provider.send_text(
                        item.chat_id,
                        f"📋 Found <b>{len(pending_approvals)}</b> pending approval(s) for <b>{html.escape(linked.name)}</b>:",
                    )
                    for app_item in pending_approvals:
                        proposal = dict(app_item.proposal_payload or {})
                        proposal["approval_id"] = str(app_item.id)
                        await provider.send_approval(item.chat_id, proposal)

            elif cmd == "/help":
                help_text = (
                    "📖 <b>Paytm ONE Vyapar Bot Guide</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "• <code>/start</code> - Bot introduction and Chat ID\n"
                    "• <code>/connect &lt;phone&gt;</code> - Link your merchant account\n"
                    "• <code>/status</code> - View pending purchase approvals\n"
                    "• <code>/help</code> - Show this assistance message\n\n"
                    "When an automated reorder recommendation is ready, you will receive "
                    "an interactive card with <b>[Approve]</b>, <b>[Modify]</b>, and <b>[Decline]</b> buttons."
                )
                await provider.send_text(item.chat_id, help_text)

    return {"received": accepted, "status": "processed"}
