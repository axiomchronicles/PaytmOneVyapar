import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from conftest import MERCHANT_ID, PRODUCT_ID, STORE_ID
from langgraph.checkpoint.memory import InMemorySaver

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
from app.infrastructure.db.models import Sale, Supplier
from app.integrations.suppliers.mock_supplier import MockSupplierAdapter
from app.ml.demand.baseline import BaselineForecaster


def test_authenticated_shortage_to_order_history_flow(client, db_factory, settings) -> None:
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
            for day in range(14):
                session.add(
                    Sale(
                        merchant_id=MERCHANT_ID,
                        store_id=STORE_ID,
                        product_id=PRODUCT_ID,
                        quantity=Decimal("3"),
                        unit_price=Decimal("600"),
                        sold_at=datetime.now(UTC) - timedelta(days=day),
                    )
                )

    asyncio.run(prepare())
    auth = client.post(
        "/api/v1/auth/token",
        data={"username": "merchant@example.com", "password": "correct-password"},
    )
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
    assert client.get("/api/v1/inventory", headers=headers).json()[0]["is_low"] is True
    assert client.get("/api/v1/recommendations", headers=headers).json()
    run = client.post(
        "/api/v1/agents/runs",
        headers=headers,
        json={
            "request_id": "full-business-flow",
            "store_id": str(STORE_ID),
            "sku": "COLD-COLA-300",
            "required_quantity": 2,
            "target_price": 450,
            "max_price": 480,
            "delivery_deadline": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    )
    assert run.status_code == 202, run.text
    waiting = run.json()["state"]
    assert waiting["approval_status"] == "PENDING"
    approval_id = waiting["approval_id"]
    assert client.get("/api/v1/a2a/activity", headers=headers).json()["items"]
    approved = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers=headers,
        json={
            "approval_token": waiting["approval_token"],
            "request_id": "full-business-flow",
            "idempotency_key": "full-business-flow-approval",
        },
    )
    assert approved.status_code == 200, approved.text
    order_id = approved.json()["workflow"]["execution_result"]["order_id"]
    assert client.get(f"/api/v1/orders/{order_id}", headers=headers).json()["status"] == "CONFIRMED"
    assert client.get("/api/v1/notifications", headers=headers).json()["items"]
    assert client.get("/api/v1/history/activity", headers=headers).json()["items"]
