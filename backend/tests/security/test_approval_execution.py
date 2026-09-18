from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.agents.services import InMemoryApprovalAuthority, SecureMemoryTransactionExecutor
from app.core.errors import AuthorizationError
from app.core.security import utc_now
from app.domain.entities import PurchaseProposal, PurchaseRequest
from app.domain.enums import ApprovalStatus
from app.integrations.suppliers.mock_supplier import MockSupplierAdapter


async def test_modified_payload_cannot_use_old_approval() -> None:
    supplier = MockSupplierAdapter(latency_seconds=0)
    authority = InMemoryApprovalAuthority("approval-secret-longer-than-32-characters")
    executor = SecureMemoryTransactionExecutor(authority, [supplier])
    proposal = PurchaseProposal(
        proposal_id=uuid4(),
        merchant_id=uuid4(),
        store_id=uuid4(),
        supplier_id=supplier.supplier_id,
        sku="COLD-COLA-300",
        quantity=3,
        unit="crate",
        unit_price=Decimal("470"),
        delivery_at=utc_now() + timedelta(days=1),
        quote_id="quote-security-test",
    )
    approval, token = await authority.request(proposal)
    await authority.decide(
        approval.approval_id,
        merchant_id=proposal.merchant_id,
        action=ApprovalStatus.APPROVED,
        token=token,
    )
    tampered = proposal.model_copy(update={"quantity": Decimal("30")})
    with pytest.raises(AuthorizationError):
        await executor.execute(
            tampered,
            approval_id=approval.approval_id,
            approval_token=token,
            idempotency_key="security-order-1",
        )


async def test_executor_is_idempotent_after_valid_approval() -> None:
    supplier = MockSupplierAdapter(latency_seconds=0)
    proposal_request = PurchaseRequest(
        sku="COLD-COLA-300",
        quantity=3,
        unit="crate",
        target_price=450,
        max_price=480,
        delivery_deadline=utc_now() + timedelta(days=2),
        merchant_id=uuid4(),
        store_id=uuid4(),
    )
    quote = await supplier.quote(proposal_request)
    proposal = PurchaseProposal(
        proposal_id=uuid4(),
        merchant_id=proposal_request.merchant_id,
        store_id=proposal_request.store_id,
        supplier_id=supplier.supplier_id,
        sku=quote.sku,
        quantity=proposal_request.quantity,
        unit="crate",
        unit_price=quote.unit_price,
        delivery_at=quote.delivery_at,
        quote_id=quote.quote_id,
    )
    authority = InMemoryApprovalAuthority("approval-secret-longer-than-32-characters")
    approval, token = await authority.request(proposal)
    await authority.decide(
        approval.approval_id,
        merchant_id=proposal.merchant_id,
        action=ApprovalStatus.APPROVED,
        token=token,
    )
    executor = SecureMemoryTransactionExecutor(authority, [supplier])
    first = await executor.execute(
        proposal,
        approval_id=approval.approval_id,
        approval_token=token,
        idempotency_key="security-order-2",
    )
    second = await executor.execute(
        proposal,
        approval_id=approval.approval_id,
        approval_token=token,
        idempotency_key="security-order-2",
    )
    assert first == second
    assert len(supplier._orders) == 1
