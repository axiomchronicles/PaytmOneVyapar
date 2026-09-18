import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from langgraph.checkpoint.memory import InMemorySaver

from app.agents.graph import build_purchase_graph
from app.agents.runtime import WorkflowRuntime
from app.agents.services import (
    InMemoryApprovalAuthority,
    SecureMemoryTransactionExecutor,
    WorkflowServices,
)
from app.domain.enums import ApprovalStatus
from app.integrations.suppliers.mock_supplier import MockSupplierAdapter
from app.ml.demand.baseline import BaselineForecaster


async def run_demo() -> dict:
    secret = "demo-approval-secret-with-32-characters"
    supplier = MockSupplierAdapter(signing_secret="demo-a2a-secret-with-32-characters")
    approvals = InMemoryApprovalAuthority(secret)
    services = WorkflowServices(
        forecast_model=BaselineForecaster(),
        suppliers=[supplier],
        approval_authority=approvals,
        transaction_executor=SecureMemoryTransactionExecutor(approvals, [supplier]),
    )
    runtime = WorkflowRuntime(
        build_purchase_graph(services, checkpointer=InMemorySaver()), approvals
    )
    merchant_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    initial = {
        "merchant_id": str(merchant_id),
        "store_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "request_id": "demo-low-inventory-001",
        "sku": "COLD-COLA-300",
        "required_quantity": 0,
        "unit": "crate",
        "target_price": 450,
        "max_price": 480,
        "spending_limit": 50000,
        "delivery_requirement": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "inventory_snapshot": {
            "quantity_on_hand": 3,
            "reorder_point": 8,
            "safety_stock": 2,
            "captured_at": datetime.now(UTC).isoformat(),
        },
        "sales_history": [
            {
                "date": (datetime.now(UTC) - timedelta(days=day)).isoformat(),
                "sales": 7 if day <= 7 else 4,
                "inventory": 20,
                "price": 600,
            }
            for day in range(28, 0, -1)
        ],
        "trace_id": "demo-trace",
        "proposal_revision": 1,
        "attempted_supplier_ids": [],
    }
    waiting = await runtime.start(initial)
    assert waiting["approval_status"] == "PENDING"
    print("LOW INVENTORY -> DEMAND FORECAST -> SUPPLIER A2A -> NEGOTIATION -> APPROVAL")
    completed = await runtime.resume(
        merchant_id=merchant_id,
        request_id=initial["request_id"],
        action=ApprovalStatus.APPROVED,
        approval_token=waiting["approval_token"],
    )
    assert completed["execution_status"] == "VERIFIED"
    print("APPROVAL -> HASH VERIFIED -> ORDER EXECUTION -> SUPPLIER CONFIRMATION -> OUTCOME")
    print(completed["execution_result"])
    return completed


if __name__ == "__main__":
    asyncio.run(run_demo())
