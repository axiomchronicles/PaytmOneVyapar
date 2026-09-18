from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import Principal, get_current_principal
from app.infrastructure.db.models import Merchant
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("")
async def list_channels(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Overview of communication and notification channels supported by Paytm ONE Vyapar."""
    telegram_active = settings.telegram_bot_token is not None
    voice_active = settings.sarvam_api_key is not None
    email_active = settings.resend_api_key is not None

    return {
        "channels": [
            {
                "id": "telegram",
                "name": "Telegram",
                "status": "active" if telegram_active else "unconfigured",
                "is_active": telegram_active,
                "is_coming_soon": False,
                "bot_username": settings.telegram_bot_username,
                "bot_url": f"https://t.me/{settings.telegram_bot_username}",
                "description": "Interactive Telegram bot for instant reorder notifications and one-tap purchase approvals.",
                "capabilities": [
                    "interactive_approval",
                    "instant_alerts",
                    "otp_delivery",
                    "bot_commands",
                ],
            },
            {
                "id": "whatsapp",
                "name": "WhatsApp Business",
                "status": "coming_soon",
                "is_active": False,
                "is_coming_soon": True,
                "description": "Meta WhatsApp Cloud API integration is coming soon. Please use Telegram in the meantime.",
                "capabilities": ["interactive_approval", "otp_delivery"],
            },
            {
                "id": "voice",
                "name": "Sarvam Voice",
                "status": "active" if voice_active else "unconfigured",
                "is_active": voice_active,
                "is_coming_soon": False,
                "description": "Real-time bilingual voice pipeline powered by Sarvam AI.",
                "capabilities": ["realtime_audio", "speech_to_text", "text_to_speech"],
            },
            {
                "id": "email",
                "name": "Resend Email",
                "status": "active" if email_active else "unconfigured",
                "is_active": email_active,
                "is_coming_soon": False,
                "description": "Transactional notifications and one-time password delivery.",
                "capabilities": ["otp_delivery", "transactional_emails"],
            },
        ]
    }


@router.get("/merchant")
async def merchant_channel_status(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Returns the merchant's configured channel bindings (e.g. linked Telegram chat)."""
    merchant = await session.get(Merchant, principal.merchant_id)
    m_settings = dict(merchant.settings or {}) if merchant else {}

    telegram_chat_id = m_settings.get("telegram_chat_id")
    telegram_username = m_settings.get("telegram_username")

    return {
        "merchant_id": str(principal.merchant_id),
        "telegram": {
            "is_connected": telegram_chat_id is not None,
            "chat_id": telegram_chat_id,
            "username": telegram_username,
            "bot_username": settings.telegram_bot_username,
            "bot_url": f"https://t.me/{settings.telegram_bot_username}",
        },
        "whatsapp": {
            "is_connected": False,
            "status": "coming_soon",
            "phone_number": merchant.phone_number if merchant else None,
        },
    }
