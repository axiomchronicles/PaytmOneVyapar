import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from conftest import MERCHANT_ID, PRODUCT_ID, STORE_ID

from app.application.services.approval_service import ApprovalService
from app.domain.entities import PurchaseProposal
from app.infrastructure.db.models import (
    A2AMessage,
    Approval,
    AuditLog,
    Merchant,
    Negotiation,
    Notification,
    Order,
    OrderEvent,
    OrderItem,
    Supplier,
    SupplierProduct,
)
from app.infrastructure.db.repositories.approvals import ApprovalRepository


def test_paginated_merchant_contracts_are_tenant_scoped(
    client, auth_headers, db_factory, settings
) -> None:
    supplier_id = uuid4()
    other_merchant_id = uuid4()
    other_order_id = uuid4()

    async def prepare() -> UUID:
        async with db_factory() as session, session.begin():
            supplier = Supplier(
                id=supplier_id,
                merchant_id=MERCHANT_ID,
                name="Contract Supplier",
                adapter_type="mock-a2a",
                trust_score=Decimal("0.91"),
            )
            session.add(supplier)
            session.add(
                SupplierProduct(
                    supplier_id=supplier_id,
                    product_id=PRODUCT_ID,
                    supplier_sku="SUP-COLA",
                    available_quantity=Decimal("40"),
                    unit_price=Decimal("455"),
                    lead_time_days=2,
                )
            )
            service = ApprovalService(
                ApprovalRepository(session),
                secret=settings.auth_approval_secret.get_secret_value(),
            )
            approval, _ = await service.create(
                PurchaseProposal(
                    proposal_id=uuid4(),
                    merchant_id=MERCHANT_ID,
                    store_id=STORE_ID,
                    supplier_id=supplier_id,
                    sku="COLD-COLA-300",
                    quantity=2,
                    unit="crate",
                    unit_price=Decimal("455"),
                    delivery_at=datetime.now(UTC) + timedelta(days=1),
                    quote_id="contract-quote",
                )
            )
            order = Order(
                merchant_id=MERCHANT_ID,
                store_id=STORE_ID,
                supplier_id=supplier_id,
                proposal_id=uuid4(),
                approval_id=approval.id,
                order_hash="1" * 64,
                status="CONFIRMED",
                total_amount=Decimal("910"),
                idempotency_key="business-contract-order",
                supplier_reference="SUP-ORDER-1",
            )
            session.add(order)
            await session.flush()
            session.add_all(
                [
                    OrderItem(
                        order_id=order.id,
                        product_id=PRODUCT_ID,
                        sku="COLD-COLA-300",
                        quantity=2,
                        unit="crate",
                        unit_price=Decimal("455"),
                    ),
                    OrderEvent(
                        merchant_id=MERCHANT_ID,
                        order_id=order.id,
                        status="CONFIRMED",
                        details={"supplier_reference": "SUP-ORDER-1"},
                    ),
                    Negotiation(
                        merchant_id=MERCHANT_ID,
                        store_id=STORE_ID,
                        supplier_id=supplier_id,
                        correlation_id=uuid4(),
                        workflow_request_id="contract-negotiation",
                        sku="COLD-COLA-300",
                        status="ACCEPTED",
                        round_count=2,
                        constraints={"max_price": "480"},
                        history=[{"status": "ACCEPTED", "unit_price": "455"}],
                        current_quote={"unit_price": "455"},
                    ),
                    Notification(
                        merchant_id=MERCHANT_ID,
                        notification_type="ORDER_UPDATE",
                        title="Order confirmed",
                        body="Supplier confirmed the order.",
                        entity_type="order",
                        entity_id=order.id,
                    ),
                    AuditLog(
                        merchant_id=MERCHANT_ID,
                        actor_type="USER",
                        actor_id="test",
                        action="order.viewed",
                        resource_type="order",
                        resource_id=str(order.id),
                    ),
                    A2AMessage(
                        merchant_id=MERCHANT_ID,
                        supplier_id=supplier_id,
                        message_id=uuid4(),
                        correlation_id=uuid4(),
                        trace_id="contract-trace",
                        sender_agent_id=uuid4(),
                        receiver_agent_id=uuid4(),
                        intent="QUOTE",
                        direction="INBOUND",
                        status="RECEIVED",
                        nonce="contract-nonce-123456",
                        idempotency_key="contract-a2a-idempotency",
                        envelope={},
                        expires_at=datetime.now(UTC) + timedelta(minutes=5),
                    ),
                ]
            )
            session.add(Merchant(id=other_merchant_id, name="Other Merchant"))
            session.add(
                Order(
                    id=other_order_id,
                    merchant_id=other_merchant_id,
                    store_id=STORE_ID,
                    supplier_id=supplier_id,
                    proposal_id=uuid4(),
                    order_hash="2" * 64,
                    status="CONFIRMED",
                    total_amount=Decimal("1"),
                    idempotency_key="other-order",
                )
            )
            return approval.id

    approval_id = asyncio.run(prepare())
    for path in (
        "/api/v1/approvals",
        "/api/v1/orders",
        "/api/v1/suppliers",
        "/api/v1/negotiations",
        "/api/v1/a2a/activity",
        "/api/v1/history/activity",
        "/api/v1/notifications",
    ):
        response = client.get(path, headers=auth_headers)
        assert response.status_code == 200, (path, response.text)
        assert "items" in response.json() and "next_cursor" in response.json()

    approval = client.get(f"/api/v1/approvals/{approval_id}", headers=auth_headers)
    assert approval.status_code == 200
    assert approval.json()["action_token"]
    order_id = client.get("/api/v1/orders", headers=auth_headers).json()["items"][0]["id"]
    order = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert order.status_code == 200
    assert order.json()["items"][0]["sku"] == "COLD-COLA-300"
    assert [event["status"] for event in order.json()["timeline"]] == [
        "APPROVAL_PENDING",
        "CONFIRMED",
    ]
    assert client.get(f"/api/v1/orders/{other_order_id}", headers=auth_headers).status_code == 404


def test_notification_read_and_analytics_drilldowns(client, auth_headers, db_factory) -> None:
    async def notification_id() -> UUID:
        async with db_factory() as session, session.begin():
            row = Notification(
                merchant_id=MERCHANT_ID,
                notification_type="ORDER_UPDATE",
                title="Test",
                body="Test notification",
            )
            session.add(row)
            await session.flush()
            return row.id

    item_id = asyncio.run(notification_id())
    marked = client.patch(f"/api/v1/notifications/{item_id}/read", headers=auth_headers)
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert client.post("/api/v1/notifications/read-all", headers=auth_headers).status_code == 204
    for path in (
        "/api/v1/analytics/overview",
        "/api/v1/analytics/sales",
        "/api/v1/analytics/inventory",
        "/api/v1/analytics/procurement",
    ):
        response = client.get(path, headers=auth_headers)
        assert response.status_code == 200, (path, response.text)


def test_approval_expiry_idempotency_and_tenant_isolation(
    client, auth_headers, db_factory, settings
) -> None:
    supplier_id = uuid4()

    async def prepare():
        async with db_factory() as session, session.begin():
            session.add(
                Supplier(id=supplier_id, merchant_id=MERCHANT_ID, name="Approval Supplier")
            )
            service = ApprovalService(
                ApprovalRepository(session),
                secret=settings.auth_approval_secret.get_secret_value(),
            )
            proposal = PurchaseProposal(
                proposal_id=uuid4(),
                merchant_id=MERCHANT_ID,
                store_id=STORE_ID,
                supplier_id=supplier_id,
                sku="COLD-COLA-300",
                quantity=1,
                unit="crate",
                unit_price=Decimal("450"),
                delivery_at=datetime.now(UTC) + timedelta(days=1),
                quote_id="approval-idempotency-quote",
            )
            approval, token = await service.create(proposal)
            expired, expired_token = await service.create(
                proposal.model_copy(update={"proposal_id": uuid4(), "quote_id": "expired-quote"})
            )
            expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            foreign = Approval(
                merchant_id=uuid4(),
                proposal_id=uuid4(),
                order_hash="f" * 64,
                proposal_payload={},
                status="PENDING",
                nonce="foreign-approval-nonce",
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
            session.add(foreign)
            await session.flush()
            return approval.id, token, expired.id, expired_token, foreign.id

    approval_id, token, expired_id, expired_token, foreign_id = asyncio.run(prepare())
    body = {"approval_token": token, "idempotency_key": "same-approval-action"}
    first = client.post(
        f"/api/v1/approvals/{approval_id}/approve", headers=auth_headers, json=body
    )
    second = client.post(
        f"/api/v1/approvals/{approval_id}/approve", headers=auth_headers, json=body
    )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()

    expired = client.post(
        f"/api/v1/approvals/{expired_id}/approve",
        headers=auth_headers,
        json={"approval_token": expired_token, "idempotency_key": "expired-action"},
    )
    assert expired.status_code == 409
    assert client.get(f"/api/v1/approvals/{foreign_id}", headers=auth_headers).status_code == 404
