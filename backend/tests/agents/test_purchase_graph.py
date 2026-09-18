from conftest import MERCHANT_ID, workflow_state
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


def runtime(*, supplier: MockSupplierAdapter | None = None):
    supplier = supplier or MockSupplierAdapter(latency_seconds=0)
    authority = InMemoryApprovalAuthority("test-approval-secret-longer-than-32")
    services = WorkflowServices(
        forecast_model=BaselineForecaster(),
        suppliers=[supplier],
        approval_authority=authority,
        transaction_executor=SecureMemoryTransactionExecutor(authority, [supplier]),
    )
    return (
        WorkflowRuntime(build_purchase_graph(services, checkpointer=InMemorySaver()), authority),
        supplier,
    )


async def test_normal_purchase_waits_for_approval_then_executes() -> None:
    engine, supplier = runtime()
    waiting = await engine.start(workflow_state())
    assert waiting["approval_status"] == "PENDING"
    assert waiting["negotiated_price"] <= 480
    assert waiting["execution_status"] if "execution_status" in waiting else True
    completed = await engine.resume(
        merchant_id=MERCHANT_ID,
        request_id="test-purchase-request",
        action=ApprovalStatus.APPROVED,
        approval_token=waiting["approval_token"],
    )
    assert completed["execution_status"] == "VERIFIED"
    assert completed["execution_result"]["supplier_confirmation"].startswith("BWW-")
    assert len(supplier._message_results) == 3


async def test_rejection_closes_without_execution() -> None:
    engine, _ = runtime()
    waiting = await engine.start(workflow_state())
    rejected = await engine.resume(
        merchant_id=MERCHANT_ID,
        request_id="test-purchase-request",
        action=ApprovalStatus.REJECTED,
        approval_token=waiting["approval_token"],
    )
    assert rejected["approval_status"] == "REJECTED"
    assert "execution_result" not in rejected


async def test_modification_creates_new_hash_and_approval() -> None:
    engine, _ = runtime()
    waiting = await engine.start(workflow_state())
    revised = await engine.resume(
        merchant_id=MERCHANT_ID,
        request_id="test-purchase-request",
        action=ApprovalStatus.MODIFIED,
        approval_token=waiting["approval_token"],
        quantity=2,
    )
    assert revised["approval_status"] == "PENDING"
    assert revised["proposal"]["quantity"] == "2.0"
    assert revised["approval_id"] != waiting["approval_id"]
    assert revised["order_hash"] != waiting["order_hash"]


async def test_risk_failure_stops_before_approval() -> None:
    engine, _ = runtime()
    state = workflow_state(spending_limit=1)
    result = await engine.start(state)
    assert result["failure_reason"].startswith("risk_failed")
    assert "approval_id" not in result


async def test_supplier_failure_stops_safely() -> None:
    engine, _ = runtime(supplier=MockSupplierAdapter(latency_seconds=0, fail_every=1))
    result = await engine.start(workflow_state())
    assert result["failure_reason"] == "supplier_unavailable"
    assert "approval_id" not in result


async def test_execution_failure_enters_recovery_and_exhausts_supplier() -> None:
    engine, _ = runtime(supplier=MockSupplierAdapter(latency_seconds=0, fail_every=3))
    waiting = await engine.start(workflow_state())
    result = await engine.resume(
        merchant_id=MERCHANT_ID,
        request_id="test-purchase-request",
        action=ApprovalStatus.APPROVED,
        approval_token=waiting["approval_token"],
    )
    assert result["execution_status"] == "FAILED"
    assert result["failure_reason"] == "supplier_unavailable"
