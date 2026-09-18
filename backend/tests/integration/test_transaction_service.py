from datetime import timedelta
from uuid import uuid4

from conftest import MERCHANT_ID, STORE_ID, USER_ID
from sqlalchemy import func, select

from app.application.services.approval_service import ApprovalService
from app.application.services.order_service import OrderService
from app.core.security import utc_now
from app.domain.entities import PurchaseProposal, PurchaseRequest
from app.infrastructure.db.models import Supplier, Transaction
from app.infrastructure.db.repositories.approvals import ApprovalRepository
from app.infrastructure.db.repositories.orders import OrderRepository
from app.integrations.suppliers.mock_supplier import MockSupplierAdapter


async def test_database_transaction_service_executes_once(db_factory, settings) -> None:
    supplier = MockSupplierAdapter(latency_seconds=0)
    request = PurchaseRequest(
        sku="COLD-COLA-300",
        quantity=2,
        unit="crate",
        target_price=450,
        max_price=480,
        delivery_deadline=utc_now() + timedelta(days=2),
        merchant_id=MERCHANT_ID,
        store_id=STORE_ID,
    )
    quote = await supplier.quote(request)
    proposal = PurchaseProposal(
        proposal_id=uuid4(),
        merchant_id=MERCHANT_ID,
        store_id=STORE_ID,
        supplier_id=supplier.supplier_id,
        sku=request.sku,
        quantity=request.quantity,
        unit=request.unit,
        unit_price=quote.unit_price,
        delivery_at=quote.delivery_at,
        quote_id=quote.quote_id,
    )
    secret = settings.auth_approval_secret.get_secret_value()
    async with db_factory() as session, session.begin():
        session.add(
            Supplier(
                id=supplier.supplier_id,
                merchant_id=MERCHANT_ID,
                name=supplier.name,
                adapter_type="mock-a2a",
            )
        )
        approvals = ApprovalRepository(session)
        approval_service = ApprovalService(approvals, secret=secret)
        approval, token = await approval_service.create(proposal)
        await approval_service.approve(
            approval.id,
            merchant_id=MERCHANT_ID,
            user_id=USER_ID,
            token=token,
        )
        service = OrderService(
            session,
            approvals,
            OrderRepository(session),
            approval_service,
            supplier,
        )
        first = await service.execute(
            approval.id,
            merchant_id=MERCHANT_ID,
            approval_token=token,
            idempotency_key="database-order-execution-1",
        )
        assert first.status == "CONFIRMED"

    async with db_factory() as session, session.begin():
        approvals = ApprovalRepository(session)
        service = OrderService(
            session,
            approvals,
            OrderRepository(session),
            ApprovalService(approvals, secret=secret),
            supplier,
        )
        second = await service.execute(
            approval.id,
            merchant_id=MERCHANT_ID,
            approval_token=token,
            idempotency_key="database-order-execution-1",
        )
        transaction_count = await session.scalar(select(func.count(Transaction.id)))
    assert first.id == second.id
    assert transaction_count == 1
