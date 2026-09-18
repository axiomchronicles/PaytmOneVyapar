from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.channels.telegram.approval_handler import (
    TelegramApprovalAction,
    parse_approval_callback,
)
from app.channels.telegram.client import TelegramChannel
from app.channels.telegram.formatter import format_decision_confirmation
from app.channels.telegram.webhook import parse_telegram_webhook
from app.core.errors import ProviderAuthenticationError
from app.infrastructure.db.models import ChannelMessage
from app.integrations.telegram.client import TelegramBotProvider, verify_telegram_secret


def test_telegram_approval_callback_is_strictly_parsed() -> None:
    approval_id = uuid4()
    callback = parse_approval_callback(f"approval:{approval_id}:APPROVE")
    assert callback.approval_id == approval_id
    assert callback.action == TelegramApprovalAction.APPROVE

    callback_mod = parse_approval_callback(f"approval:{approval_id}:MODIFY")
    assert callback_mod.action == TelegramApprovalAction.MODIFY

    callback_rej = parse_approval_callback(f"approval:{approval_id}:REJECT")
    assert callback_rej.action == TelegramApprovalAction.REJECT

    with pytest.raises(ValueError, match="Invalid Telegram approval callback format"):
        parse_approval_callback("invalid:payload")

    with pytest.raises(ValueError):
        parse_approval_callback("other:123:APPROVE")


def test_telegram_formatter_helpers() -> None:
    text_approve = format_decision_confirmation("COLD-COLA-300", "APPROVE", total_amount="4500.00")
    assert "✅" in text_approve
    assert "PURCHASE ORDER APPROVED" in text_approve
    assert "4500.00" in text_approve

    text_reject = format_decision_confirmation("COLD-COLA-300", "REJECT")
    assert "❌" in text_reject
    assert "PURCHASE ORDER DECLINED" in text_reject

    text_modify = format_decision_confirmation("COLD-COLA-300", "MODIFY", quantity="15")
    assert "✏️" in text_modify
    assert "15" in text_modify


def test_telegram_webhook_parser() -> None:
    # 1. Test callback query
    cb_payload = {
        "update_id": 1001,
        "callback_query": {
            "id": "cb_12345",
            "from": {"id": 998877, "first_name": "Rohan", "username": "rohan_sh"},
            "message": {
                "message_id": 42,
                "chat": {"id": 998877, "type": "private"},
                "text": "Approval required",
            },
            "data": f"approval:{uuid4()}:APPROVE",
        },
    }
    inbound = parse_telegram_webhook(cb_payload)
    assert len(inbound) == 1
    item = inbound[0]
    assert item.kind == "callback_query"
    assert item.update_id == 1001
    assert item.message_id == "cb:cb_12345"
    assert item.chat_id == "998877"
    assert item.sender_id == "998877"
    assert item.username == "rohan_sh"
    assert item.callback_data.startswith("approval:")

    # 2. Test message command
    msg_payload = {
        "update_id": 1002,
        "message": {
            "message_id": 43,
            "from": {"id": 998877, "first_name": "Rohan"},
            "chat": {"id": 998877, "type": "private"},
            "text": "/start",
        },
    }
    inbound_msg = parse_telegram_webhook(msg_payload)
    assert len(inbound_msg) == 1
    assert inbound_msg[0].kind == "command"
    assert inbound_msg[0].text == "/start"
    assert inbound_msg[0].message_id == "msg:43"


def test_verify_telegram_secret() -> None:
    assert verify_telegram_secret(None, None) is True
    assert verify_telegram_secret("my-secret", "my-secret") is True
    assert verify_telegram_secret("wrong-secret", "my-secret") is False
    assert verify_telegram_secret(None, "my-secret") is False


@pytest.mark.asyncio
async def test_telegram_bot_provider_send_text() -> None:
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 789, "chat": {"id": 12345}}},
        )
    )
    async with httpx.AsyncClient(transport=mock_transport) as client:
        provider = TelegramBotProvider(bot_token="test-token", client=client)
        msg_id = await provider.send_text("12345", "Hello Merchant!")
        assert msg_id == "789"


@pytest.mark.asyncio
async def test_telegram_bot_provider_send_approval() -> None:
    captured_payload = {}

    def handler(req: httpx.Request) -> httpx.Response:
        import json

        nonlocal captured_payload
        captured_payload = json.loads(req.content.decode())
        return httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 999}},
        )

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        provider = TelegramBotProvider(bot_token="test-token", client=client)
        proposal = {
            "approval_id": str(uuid4()),
            "sku": "AMUL-BUTTER-500",
            "quantity": "20",
            "unit": "packs",
            "unit_price": "250.00",
            "total_amount": "5000.00",
            "currency": "INR",
        }
        msg_id = await provider.send_approval("12345", proposal)
        assert msg_id == "999"
        assert captured_payload["chat_id"] == "12345"
        assert "AMUL-BUTTER-500" in captured_payload["text"]
        assert "reply_markup" in captured_payload
        buttons = captured_payload["reply_markup"]["inline_keyboard"]
        assert any("Approve" in btn["text"] for row in buttons for btn in row)


@pytest.mark.asyncio
async def test_telegram_bot_provider_auth_failure() -> None:
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(401, text="Unauthorized: invalid token")
    )
    async with httpx.AsyncClient(transport=mock_transport) as client:
        provider = TelegramBotProvider(bot_token="bad-token", client=client)
        with pytest.raises(ProviderAuthenticationError):
            await provider.get_me()


@pytest.mark.asyncio
async def test_telegram_bot_provider_retry_on_server_error() -> None:
    calls = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json={"ok": True, "result": {"id": 1, "username": "test_bot"}})

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        provider = TelegramBotProvider(bot_token="test-token", client=client)
        me = await provider.get_me()
        assert me["username"] == "test_bot"
        assert calls == 3


@pytest.mark.asyncio
async def test_telegram_channel_send_approval(db_factory) -> None:
    merchant_id = uuid4()
    mock_provider = AsyncMock()
    mock_provider.send_approval.return_value = "tg-msg-456"

    async with db_factory() as session:
        channel = TelegramChannel(mock_provider, session)
        proposal = {
            "approval_id": str(uuid4()),
            "sku": "CHAI-PATTI-1KG",
            "quantity": "5",
            "unit": "kg",
            "unit_price": "350.00",
            "total_amount": "1750.00",
            "currency": "INR",
        }
        result_id = await channel.send_approval(
            merchant_id=merchant_id,
            recipient="987654321",
            proposal=proposal,
            idempotency_key="idemp-tg-01",
        )
        assert result_id == "tg-msg-456"

        # Verify channel message persisted in database
        from sqlalchemy import select

        msg = await session.scalar(
            select(ChannelMessage).where(ChannelMessage.idempotency_key == "idemp-tg-01")
        )
        assert msg is not None
        assert msg.channel == "TELEGRAM"
        assert msg.direction == "OUTBOUND"
        assert msg.provider_message_id == "tg-msg-456"
        assert msg.status == "SENT"


@pytest.mark.asyncio
async def test_telegram_otp_delivery() -> None:
    from app.application.services.auth_service import TelegramOtpDelivery

    mock_send = AsyncMock()
    mock_send.return_value = "msg-otp-1"
    otp_delivery = TelegramOtpDelivery(mock_send)

    await otp_delivery.send("12345678", "849201", idempotency_key="key-otp-tg")
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[0] == "12345678"
    assert "849201" in args[1]
    assert kwargs["idempotency_key"] == "key-otp-tg"


@pytest.mark.asyncio
async def test_multichannel_otp_delivery_routes_to_telegram() -> None:
    from app.application.services.auth_service import MultiChannelOtpDelivery

    mock_tg = AsyncMock()
    mock_email = AsyncMock()
    delivery = MultiChannelOtpDelivery(telegram=mock_tg, email=mock_email)

    # Phone delivery routes to Telegram
    await delivery.send("9876543210", "123456", idempotency_key="idemp-1")
    mock_tg.send.assert_called_once_with("9876543210", "123456", idempotency_key="idemp-1")
    mock_email.send.assert_not_called()

    # Email delivery routes to Email
    await delivery.send("user@test.com", "654321", idempotency_key="idemp-2")
    mock_email.send.assert_called_once_with("user@test.com", "654321", idempotency_key="idemp-2")
