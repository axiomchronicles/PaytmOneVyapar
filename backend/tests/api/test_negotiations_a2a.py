import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from conftest import MERCHANT_ID, PRODUCT_ID, STORE_ID
from langgraph.checkpoint.memory import InMemorySaver

from app.a2a.schemas import A2AEnvelope, A2AIntent, PurchaseRequestPayload
from app.a2a.signing import sign_envelope, verify_envelope
from app.agents.graph import build_purchase_graph
from app.agents.runtime import WorkflowRuntime
from app.agents.services import (
    DatabaseApprovalAuthority,
    DatabaseTransactionExecutor,
    WorkflowServices,
)
from app.application.services.activity_service import (
    DatabaseA2ARecorder,
    DatabaseWorkflowActivityRecorder,
)
from app.core.errors import InvalidSignatureError
from app.domain.enums import NegotiationStatus
from app.infrastructure.db.models import A2AMessage, Negotiation, Sale, Supplier
from app.integrations.suppliers.mock_supplier import MockSupplierAdapter
from app.ml.demand.baseline import BaselineForecaster


def test_a2a_envelope_signing_and_verification(settings):
    secret = settings.a2a_signing_secret.get_secret_value()
    now = datetime.now(UTC)
    sender_id = uuid4()
    receiver_id = uuid4()

    payload = PurchaseRequestPayload(
        merchant_id=uuid4(),
        store_id=uuid4(),
        sku="COLD-COLA-300",
        quantity="10",
        unit="crate",
        target_price="430.00",
        max_price="475.00",
        delivery_deadline=now + timedelta(days=2),
    )
    unsigned = A2AEnvelope(
        message_id=uuid4(),
        correlation_id=uuid4(),
        trace_id="trace-001",
        sender_agent_id=sender_id,
        receiver_agent_id=receiver_id,
        intent=A2AIntent.PURCHASE_REQUEST,
        timestamp=now,
        expires_at=now + timedelta(minutes=5),
        nonce="test-nonce-123456",
        payload=payload.model_dump(mode="json", exclude={"intent"}),
        signature="0" * 64,
        idempotency_key="test-idemp-001",
    )

    sig = sign_envelope(unsigned, secret)
    signed = unsigned.model_copy(update={"signature": sig})

    # Verification does not raise for valid signed envelope
    verify_envelope(signed, secret=secret, expected_receiver_id=str(receiver_id))

    # Tampering payload invalidates signature
    tampered = signed.model_copy(update={"payload": {**signed.payload, "target_price": "100.00"}})
    with pytest.raises(InvalidSignatureError):
        verify_envelope(tampered, secret=secret, expected_receiver_id=str(receiver_id))


async def test_list_and_get_negotiations_api(client, db_factory, auth_headers):
    supplier_id = uuid4()
    nego_id = uuid4()
    correlation_id = uuid4()
    empty_correlation_id = uuid4()
    now = datetime.now(UTC)

    async with db_factory() as session, session.begin():
        supplier = Supplier(
            id=supplier_id,
            name="Bharat Beverage Wholesale",
            city="Bengaluru",
            pincode="560038",
            trust_score=Decimal("0.9800"),
        )
        negotiation = Negotiation(
            id=nego_id,
            merchant_id=MERCHANT_ID,
            store_id=STORE_ID,
            supplier_id=supplier_id,
            correlation_id=correlation_id,
            workflow_request_id="req_test_nego_001",
            sku="COLD-COLA-300",
            status=NegotiationStatus.ACCEPTED,
            round_count=3,
            constraints={"target_price": "435.00", "max_price": "480.00", "quantity": "10"},
            history=[
                {"round": 1, "status": "INITIAL_QUOTE", "unit_price": "470.00"},
                {"round": 2, "status": "COUNTER_OFFER", "unit_price": "435.00"},
                {"round": 2, "status": "ACCEPTED", "unit_price": "441.80"},
            ],
            current_quote={"quote_id": "mock-q-1", "unit_price": "441.80"},
        )
        a2a_msg = A2AMessage(
            id=uuid4(),
            merchant_id=MERCHANT_ID,
            supplier_id=supplier_id,
            negotiation_id=nego_id,
            message_id=uuid4(),
            correlation_id=correlation_id,
            trace_id="test-trace-001",
            sender_agent_id=uuid4(),
            receiver_agent_id=uuid4(),
            intent="QUOTE",
            direction="INBOUND",
            status="RECEIVED",
            nonce="nonce-test-123456",
            idempotency_key="idemp-test-a2a-001",
            envelope={"intent": "QUOTE", "unit_price": "470.00"},
            expires_at=now + timedelta(minutes=15),
            processed_at=now,
        )
        session.add_all([supplier, negotiation, a2a_msg])
        session.add(
            Negotiation(
                merchant_id=MERCHANT_ID,
                store_id=STORE_ID,
                supplier_id=supplier_id,
                correlation_id=empty_correlation_id,
                workflow_request_id="catalog-without-a2a-envelopes",
                sku="CATALOG-ONLY-SKU",
                status=NegotiationStatus.ACCEPTED,
                round_count=1,
                constraints={},
                history=[],
            )
        )

    # Test list negotiations
    response = client.get("/api/v1/negotiations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    item = next(i for i in data["items"] if i["id"] == str(nego_id))
    assert item["sku"] == "COLD-COLA-300"
    assert item["supplier_name"] == "Bharat Beverage Wholesale"
    assert item["round_count"] == 3
    assert item["status"] == "ACCEPTED"

    # Test get negotiation detail
    detail_res = client.get(f"/api/v1/negotiations/{nego_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == str(nego_id)
    assert len(detail["history"]) == 3
    assert detail["history"][0]["status"] == "INITIAL_QUOTE"
    assert detail["history"][1]["status"] == "COUNTER_OFFER"
    assert detail["history"][2]["status"] == "ACCEPTED"

    # Test conversation endpoint
    conv_res = client.get(f"/api/v1/a2a/conversations/{correlation_id}", headers=auth_headers)
    assert conv_res.status_code == 200
    conv = conv_res.json()
    assert len(conv) >= 1
    assert conv[0]["intent"] == "QUOTE"
    assert conv[0]["direction"] == "INBOUND"

    empty_conv = client.get(
        f"/api/v1/a2a/conversations/{empty_correlation_id}", headers=auth_headers
    )
    assert empty_conv.status_code == 200
    assert empty_conv.json() == []


def test_start_negotiation_api(client, db_factory, settings, auth_headers):
    supplier = MockSupplierAdapter(
        latency_seconds=0,
        signing_secret=settings.a2a_signing_secret.get_secret_value(),
        buyer_agent_id=settings.a2a_agent_id,
        message_recorder=DatabaseA2ARecorder(db_factory),
    )
    authority = DatabaseApprovalAuthority(
        db_factory,
        secret=settings.auth_approval_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.auth_approval_token_minutes,
    )
    client.app.state.workflow_runtime = WorkflowRuntime(
        build_purchase_graph(
            WorkflowServices(
                forecast_model=BaselineForecaster(),
                suppliers=[supplier],
                approval_authority=authority,
                transaction_executor=DatabaseTransactionExecutor(db_factory, authority, [supplier]),
                activity_recorder=DatabaseWorkflowActivityRecorder(db_factory),
            ),
            checkpointer=InMemorySaver(),
        ),
        authority,
    )

    async def prepare() -> None:
        async with db_factory() as session, session.begin():
            session.add(
                Supplier(
                    id=supplier.supplier_id,
                    merchant_id=MERCHANT_ID,
                    name=supplier.name,
                    adapter_type="mock-a2a",
                )
            )
            now = datetime.now(UTC)
            for days_ago in range(14, 0, -1):
                session.add(
                    Sale(
                        id=uuid4(),
                        merchant_id=MERCHANT_ID,
                        store_id=STORE_ID,
                        product_id=PRODUCT_ID,
                        quantity=Decimal("3"),
                        unit_price=Decimal("600"),
                        sold_at=now - timedelta(days=days_ago),
                        signals={"temperature_c": 30},
                    )
                )

    asyncio.run(prepare())

    response = client.post(
        "/api/v1/negotiations/start",
        json={
            "sku": "COLD-COLA-300",
            "supplier_id": str(supplier.supplier_id),
            "quantity": 10,
            "target_price": 435.0,
            "max_price": 480.0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "COLD-COLA-300"
    assert data["supplier_id"] == str(supplier.supplier_id)
    assert data["status"] == "ACCEPTED"
    assert data["approval_id"]
    approval = client.get(f"/api/v1/approvals/{data['approval_id']}", headers=auth_headers)
    assert approval.status_code == 200
    assert approval.json()["proposal_id"] == data["proposal_id"]
    assert "history" in data
    assert len(data["history"]) >= 1
    assert data["round_count"] >= 2
