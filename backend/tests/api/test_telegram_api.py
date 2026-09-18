from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from pydantic import SecretStr

from app.core.security import canonical_order_hash, utc_now
from app.domain.enums import ApprovalStatus
from app.infrastructure.db.models import Approval, Merchant
from tests.conftest import MERCHANT_ID


def test_telegram_status_endpoint(client) -> None:
    response = client.get("/webhooks/telegram")
    assert response.status_code == 200
    data = response.json()
    assert data["channel"] == "TELEGRAM"
    assert "bot_username" in data
    assert "bot_url" in data


def test_channels_endpoint_lists_all_channels(client) -> None:
    response = client.get("/api/v1/channels")
    assert response.status_code == 200
    data = response.json()
    channels = {c["id"]: c for c in data["channels"]}

    assert "telegram" in channels
    assert channels["telegram"]["status"] == "active"
    assert channels["telegram"]["is_active"] is True
    assert channels["telegram"]["is_coming_soon"] is False
    assert "bot_username" in channels["telegram"]

    assert "whatsapp" in channels
    assert channels["whatsapp"]["status"] == "coming_soon"
    assert channels["whatsapp"]["is_active"] is False
    assert channels["whatsapp"]["is_coming_soon"] is True


def test_merchant_channels_endpoint(client, auth_headers) -> None:
    response = client.get("/api/v1/channels/merchant", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "telegram" in data
    assert "whatsapp" in data
    assert data["whatsapp"]["status"] == "coming_soon"


def test_telegram_webhook_secret_validation(client, settings) -> None:
    # Mock provider so no real external calls are made
    mock_provider = AsyncMock()
    mock_provider.send_text.return_value = "101"
    client.app.state.telegram_provider = mock_provider

    settings.telegram_webhook_secret = SecretStr("secret-12345")

    payload = {
        "update_id": 9901,
        "message": {
            "message_id": 1,
            "from": {"id": 123},
            "chat": {"id": 123},
            "text": "/start",
        },
    }

    # Without secret header
    res = client.post("/webhooks/telegram", json=payload)
    assert res.status_code == 401

    # With invalid secret header
    res = client.post(
        "/webhooks/telegram",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
    )
    assert res.status_code == 401

    # With valid secret header
    res = client.post(
        "/webhooks/telegram",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret-12345"},
    )
    assert res.status_code == 200

    # Reset
    settings.telegram_webhook_secret = None


def test_telegram_start_command(client) -> None:
    app = client.app
    mock_provider = AsyncMock()
    mock_provider.send_text.return_value = "msg-123"
    app.state.telegram_provider = mock_provider

    payload = {
        "update_id": 5001,
        "message": {
            "message_id": 101,
            "from": {"id": 987654, "first_name": "Karan"},
            "chat": {"id": 987654},
            "text": "/start",
        },
    }
    response = client.post("/webhooks/telegram", json=payload)
    assert response.status_code == 200
    assert response.json()["received"] == 1
    mock_provider.send_text.assert_called_once()
    args, _ = mock_provider.send_text.call_args
    assert args[0] == "987654"
    assert "Welcome to Paytm ONE Vyapar" in args[1]


def test_telegram_connect_and_status_command(client, db_factory) -> None:
    app = client.app
    mock_provider = AsyncMock()
    mock_provider.send_text.return_value = "msg-201"
    app.state.telegram_provider = mock_provider

    # Send /connect command with seeded phone number "919000000000"
    payload = {
        "update_id": 6001,
        "message": {
            "message_id": 201,
            "from": {"id": 776655, "username": "sharma_kirana"},
            "chat": {"id": 776655},
            "text": "/connect 919000000000",
        },
    }
    res = client.post("/webhooks/telegram", json=payload)
    assert res.status_code == 200

    import asyncio

    # Verify merchant settings now has telegram_chat_id
    async def check_merchant():
        async with db_factory() as session:
            m = await session.get(Merchant, MERCHANT_ID)
            return m.settings

    updated_settings = asyncio.run(check_merchant())
    assert updated_settings.get("telegram_chat_id") == "776655"


def test_telegram_approval_callback_flow(client, db_factory, settings) -> None:
    app = client.app
    mock_provider = AsyncMock()
    mock_provider.answer_callback_query.return_value = True
    mock_provider.edit_message_text.return_value = True
    app.state.telegram_provider = mock_provider

    import asyncio

    approval_id = uuid4()

    async def seed_approval():
        async with db_factory() as session:
            proposal = {
                "approval_id": str(approval_id),
                "sku": "PARLE-G-100G",
                "quantity": 50,
                "unit": "packs",
                "unit_price": 10.0,
                "total_amount": 500.0,
                "currency": "INR",
            }
            appr = Approval(
                id=approval_id,
                merchant_id=MERCHANT_ID,
                proposal_id=uuid4(),
                order_hash=canonical_order_hash(proposal),
                proposal_payload=proposal,
                status=ApprovalStatus.PENDING,
                nonce="nonce-tg-test",
                expires_at=utc_now() + timedelta(minutes=10),
                channel="TELEGRAM",
            )
            session.add(appr)
            await session.commit()

    asyncio.run(seed_approval())

    # Simulate merchant clicking [Approve] button in Telegram
    payload = {
        "update_id": 7001,
        "callback_query": {
            "id": "query_999",
            "from": {"id": 443322, "first_name": "Test", "username": "test_merchant"},
            "message": {
                "message_id": 888,
                "chat": {"id": 443322},
                "text": "Approval required",
            },
            "data": f"approval:{approval_id}:APPROVE",
        },
    }

    res = client.post("/webhooks/telegram", json=payload)
    assert res.status_code == 200
    assert res.json()["received"] == 1

    # Check that answer_callback_query was called
    mock_provider.answer_callback_query.assert_called_once_with(
        "query_999", text="Approving order..."
    )

    # Check that message was updated with confirmation
    mock_provider.edit_message_text.assert_called_once()
    args = mock_provider.edit_message_text.call_args[0]
    assert args[0] == "443322"
    assert args[1] == 888
    assert "APPROVED" in args[2]

    # Check database approval status is now APPROVED
    async def check_status():
        async with db_factory() as session:
            appr = await session.get(Approval, approval_id)
            return appr.status

    final_status = asyncio.run(check_status())
    assert final_status == ApprovalStatus.APPROVED
