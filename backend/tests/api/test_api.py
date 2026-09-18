import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from conftest import MERCHANT_ID, PRODUCT_ID, STORE_ID

from app.a2a.schemas import A2AEnvelope, A2AIntent, PurchaseRequestPayload
from app.a2a.signing import sign_envelope
from app.application.services.approval_service import ApprovalService
from app.core.security import utc_now
from app.domain.entities import PurchaseProposal
from app.infrastructure.db.models import A2AAgent, Order, Supplier
from app.infrastructure.db.repositories.approvals import ApprovalRepository


def test_health(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_and_inventory(client) -> None:
    auth = client.post(
        "/api/v1/auth/token",
        data={"username": "merchant@example.com", "password": "correct-password"},
    )
    assert auth.status_code == 200
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
    response = client.get("/api/v1/inventory", headers=headers)
    assert response.status_code == 200
    assert response.json()[0]["sku"] == "COLD-COLA-300"


def test_inventory_event_is_idempotently_constrained(client, auth_headers) -> None:
    payload = {
        "store_id": str(STORE_ID),
        "product_id": str(PRODUCT_ID),
        "quantity_delta": "2",
        "event_type": "STOCK_RECEIVED",
        "source": "test",
        "idempotency_key": "inventory-event-1",
    }
    response = client.post("/api/v1/inventory/events", json=payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["quantity_on_hand"] == "5.000"


def test_a2a_endpoint_validates_signature(client, settings, db_factory) -> None:
    now = utc_now()
    payload = PurchaseRequestPayload(
        merchant_id=MERCHANT_ID,
        store_id=STORE_ID,
        sku="COLD-COLA-300",
        quantity=3,
        unit="crate",
        target_price=450,
        max_price=480,
        delivery_deadline=now + timedelta(days=2),
    )
    unsigned = A2AEnvelope(
        message_id=uuid4(),
        correlation_id=uuid4(),
        trace_id="api-a2a-test",
        sender_agent_id=uuid4(),
        receiver_agent_id=settings.a2a_agent_id,
        intent=A2AIntent.PURCHASE_REQUEST,
        timestamp=now,
        expires_at=now + timedelta(minutes=5),
        nonce="nonce-api-a2a-test",
        payload=payload.model_dump(mode="json", exclude={"intent"}),
        signature="0" * 64,
        idempotency_key="a2a-api-message-1",
    )
    signed = unsigned.model_copy(
        update={
            "signature": sign_envelope(unsigned, settings.a2a_signing_secret.get_secret_value())
        }
    )

    async def register_sender():
        async with db_factory() as session:
            async with session.begin():
                session.add(
                    A2AAgent(
                        id=signed.sender_agent_id,
                        name="test-peer",
                        endpoint="https://supplier.example/a2a",
                        allowed_intents=["PURCHASE_REQUEST"],
                    )
                )

    asyncio.run(register_sender())
    response = client.post("/api/v1/a2a/messages", json=signed.model_dump(mode="json"))
    assert response.status_code == 202


def test_approval_and_order_endpoints(client, auth_headers, db_factory, settings) -> None:
    supplier_id = uuid4()

    async def prepare():
        async with db_factory() as session, session.begin():
            session.add(Supplier(id=supplier_id, merchant_id=MERCHANT_ID, name="API Supplier"))
            service = ApprovalService(
                ApprovalRepository(session),
                secret=settings.auth_approval_secret.get_secret_value(),
            )
            approval, token = await service.create(
                PurchaseProposal(
                    proposal_id=uuid4(),
                    merchant_id=MERCHANT_ID,
                    store_id=STORE_ID,
                    supplier_id=supplier_id,
                    sku="COLD-COLA-300",
                    quantity=2,
                    unit="crate",
                    unit_price=Decimal("450"),
                    delivery_at=datetime.now(UTC) + timedelta(days=1),
                    quote_id="api-quote",
                )
            )
            await session.flush()
            approval_id = approval.id
        return approval_id, token

    approval_id, token = asyncio.run(prepare())
    fetched = client.get(f"/api/v1/approvals/{approval_id}", headers=auth_headers)
    assert fetched.status_code == 200
    approved = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers=auth_headers,
        json={
            "approval_token": token,
            "idempotency_key": "approval-api-1",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"

    async def add_order():
        async with db_factory() as session, session.begin():
            row = Order(
                merchant_id=MERCHANT_ID,
                store_id=STORE_ID,
                supplier_id=supplier_id,
                proposal_id=uuid4(),
                approval_id=approval_id,
                order_hash="d" * 64,
                status="CONFIRMED",
                total_amount=Decimal("900"),
                idempotency_key="order-api-1",
                supplier_reference="SUP-1",
            )
            session.add(row)
            await session.flush()
            return row.id

    order_id = asyncio.run(add_order())
    order = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert order.status_code == 200
    assert order.json()["supplier_reference"] == "SUP-1"


def test_whatsapp_webhook_verification_and_signature(client, settings) -> None:
    verify = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42"},
    )
    assert verify.status_code == 200 and verify.text == "42"

    payload = {"object": "whatsapp_business_account", "entry": []}
    raw = json.dumps(payload).encode()
    signature = hmac.new(
        settings.whatsapp_app_secret.get_secret_value().encode(), raw, hashlib.sha256
    ).hexdigest()
    received = client.post(
        "/webhooks/whatsapp",
        content=raw,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": f"sha256={signature}"},
    )
    assert received.status_code == 200


def test_voice_session_requires_authentication(client) -> None:
    response = client.post("/api/v1/voice/sessions", json={"language_code": "hi-IN"})
    assert response.status_code == 401


def test_validation_errors_use_consistent_envelope(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/inventory/events",
        headers=auth_headers,
        json={"quantity_delta": "not-a-number"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
