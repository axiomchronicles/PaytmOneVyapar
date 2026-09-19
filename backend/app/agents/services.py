import secrets
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.services.activity_service import (
    NullWorkflowActivityRecorder,
    WorkflowActivityRecorder,
)
from app.application.services.approval_service import ApprovalService
from app.application.services.negotiation_service import NegotiationService
from app.application.services.order_service import OrderService
from app.application.services.risk_service import RiskService
from app.core.errors import AuthorizationError, ConflictError, StaleApprovalError
from app.core.security import (
    canonical_order_hash,
    create_approval_token,
    decode_token,
    utc_now,
)
from app.domain.contracts import ForecastModel, SupplierAdapter, TransactionExecutor
from app.domain.entities import ApprovalRecord, OrderResult, PurchaseProposal
from app.domain.enums import ApprovalStatus
from app.infrastructure.db.repositories.approvals import ApprovalRepository

workflow_request_context: ContextVar[str | None] = ContextVar("workflow_request_id", default=None)
workflow_revision_context: ContextVar[int] = ContextVar("workflow_revision", default=1)


class ApprovalAuthority(Protocol):
    async def request(self, proposal: PurchaseProposal) -> tuple[ApprovalRecord, str]: ...

    async def decide(
        self,
        approval_id: UUID,
        *,
        merchant_id: UUID,
        action: ApprovalStatus,
        token: str,
        user_id: UUID | None = None,
    ) -> ApprovalRecord: ...

    async def get(self, approval_id: UUID) -> ApprovalRecord: ...


@dataclass
class WorkflowServices:
    forecast_model: ForecastModel
    suppliers: list[SupplierAdapter]
    approval_authority: ApprovalAuthority
    transaction_executor: TransactionExecutor
    negotiation: NegotiationService = field(default_factory=NegotiationService)
    risk: RiskService = field(default_factory=RiskService)
    activity_recorder: WorkflowActivityRecorder = field(
        default_factory=NullWorkflowActivityRecorder
    )

    def supplier(self, supplier_id: UUID) -> SupplierAdapter:
        for adapter in self.suppliers:
            if getattr(adapter, "supplier_id", None) == supplier_id:
                return adapter
        for adapter in self.suppliers:
            if getattr(adapter, "handles_all_suppliers", False):
                return adapter
        raise LookupError(f"No adapter registered for supplier {supplier_id}")


class InMemoryApprovalAuthority:
    def __init__(self, secret: str, *, ttl_minutes: int = 10) -> None:
        self.secret = secret
        self.ttl_minutes = ttl_minutes
        self.records: dict[UUID, ApprovalRecord] = {}
        self.proposals: dict[UUID, PurchaseProposal] = {}

    async def request(self, proposal: PurchaseProposal) -> tuple[ApprovalRecord, str]:
        record = ApprovalRecord(
            approval_id=uuid4(),
            proposal_id=proposal.proposal_id,
            merchant_id=proposal.merchant_id,
            order_hash=canonical_order_hash(proposal.canonical_payload()),
            nonce=secrets.token_urlsafe(24),
            status=ApprovalStatus.PENDING,
            expires_at=utc_now() + timedelta(minutes=self.ttl_minutes),
        )
        self.records[record.approval_id] = record
        self.proposals[record.approval_id] = proposal
        token = create_approval_token(
            merchant_id=record.merchant_id,
            proposal_id=record.proposal_id,
            approval_id=record.approval_id,
            order_hash=record.order_hash,
            nonce=record.nonce,
            secret=self.secret,
            ttl_minutes=self.ttl_minutes,
            expires_at=record.expires_at,
        )
        return record, token

    async def decide(
        self,
        approval_id: UUID,
        *,
        merchant_id: UUID,
        action: ApprovalStatus,
        token: str,
        user_id: UUID | None = None,
    ) -> ApprovalRecord:
        record = await self.get(approval_id)
        if record.merchant_id != merchant_id:
            raise AuthorizationError("Approval belongs to another merchant")
        if record.status != ApprovalStatus.PENDING:
            raise ConflictError("Approval has already been decided")
        if record.expires_at <= utc_now():
            self.records[approval_id] = record.model_copy(update={"status": ApprovalStatus.EXPIRED})
            raise StaleApprovalError("Approval expired")
        claims = decode_token(token, secret=self.secret)
        expected = {
            "sub": str(record.merchant_id),
            "proposal_id": str(record.proposal_id),
            "approval_id": str(record.approval_id),
            "order_hash": record.order_hash,
            "nonce": record.nonce,
            "type": "approval",
        }
        if any(claims.get(key) != value for key, value in expected.items()):
            raise AuthorizationError("Approval token does not match the proposal")
        updated = record.model_copy(update={"status": action})
        self.records[approval_id] = updated
        return updated

    async def get(self, approval_id: UUID) -> ApprovalRecord:
        try:
            return self.records[approval_id]
        except KeyError as exc:
            raise AuthorizationError("Unknown approval") from exc


class SecureMemoryTransactionExecutor:
    def __init__(
        self, approval_authority: InMemoryApprovalAuthority, suppliers: list[SupplierAdapter]
    ) -> None:
        self.approvals = approval_authority
        self.suppliers = suppliers
        self.results: dict[str, OrderResult] = {}

    async def execute(
        self,
        proposal: PurchaseProposal,
        *,
        approval_id: UUID,
        approval_token: str,
        idempotency_key: str,
    ) -> OrderResult:
        if idempotency_key in self.results:
            return self.results[idempotency_key]
        approval = await self.approvals.get(approval_id)
        if approval.status != ApprovalStatus.APPROVED:
            raise AuthorizationError("Order execution requires explicit approval")
        if approval.expires_at <= utc_now():
            raise StaleApprovalError("Approval expired")
        if approval.order_hash != canonical_order_hash(proposal.canonical_payload()):
            raise AuthorizationError("Proposal differs from the approved payload")
        claims = decode_token(approval_token, secret=self.approvals.secret)
        if (
            claims.get("approval_id") != str(approval_id)
            or claims.get("order_hash") != approval.order_hash
        ):
            raise AuthorizationError("Approval token does not authorize this proposal")
        supplier = next(
            (
                item
                for item in self.suppliers
                if getattr(item, "supplier_id", None) == proposal.supplier_id
            ),
            None,
        )
        if supplier is None:
            supplier = next(
                (item for item in self.suppliers if getattr(item, "handles_all_suppliers", False)),
                None,
            )
        if supplier is None:
            raise AuthorizationError("No supplier adapter is registered for the approved supplier")
        result = await supplier.place_order(proposal, idempotency_key=idempotency_key)
        self.results[idempotency_key] = result
        return result


class DatabaseApprovalAuthority:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        secret: str,
        algorithm: str = "HS256",
        ttl_minutes: int = 10,
    ) -> None:
        self.session_factory = session_factory
        self.secret = secret
        self.algorithm = algorithm
        self.ttl_minutes = ttl_minutes

    async def request(self, proposal: PurchaseProposal) -> tuple[ApprovalRecord, str]:
        async with self.session_factory() as session, session.begin():
            service = ApprovalService(
                ApprovalRepository(session),
                secret=self.secret,
                algorithm=self.algorithm,
                ttl_minutes=self.ttl_minutes,
            )
            row, token = await service.create(
                proposal,
                revision=workflow_revision_context.get(),
                correlation_id=workflow_request_context.get(),
            )
            row.workflow_request_id = workflow_request_context.get()
            record = self._record(row)
        return record, token

    async def decide(
        self,
        approval_id: UUID,
        *,
        merchant_id: UUID,
        action: ApprovalStatus,
        token: str,
        user_id: UUID | None = None,
    ) -> ApprovalRecord:
        async with self.session_factory() as session, session.begin():
            repository = ApprovalRepository(session)
            service = ApprovalService(
                repository,
                secret=self.secret,
                algorithm=self.algorithm,
                ttl_minutes=self.ttl_minutes,
            )
            if user_id is None:
                raise AuthorizationError("An authenticated user is required for approval")
            if action == ApprovalStatus.APPROVED:
                row = await service.approve(
                    approval_id,
                    merchant_id=merchant_id,
                    user_id=user_id,
                    token=token,
                )
            elif action == ApprovalStatus.MODIFIED:
                row = await service.mark_modified(
                    approval_id,
                    merchant_id=merchant_id,
                    user_id=user_id,
                    token=token,
                )
            elif action == ApprovalStatus.REJECTED:
                row = await service.reject(approval_id, merchant_id=merchant_id, user_id=user_id)
            else:
                raise ValueError("Unsupported approval decision")
            await session.flush()
            record = self._record(row)
        return record

    async def get(self, approval_id: UUID) -> ApprovalRecord:
        async with self.session_factory() as session:
            return self._record(await ApprovalRepository(session).get(approval_id))

    @staticmethod
    def _record(row) -> ApprovalRecord:
        return ApprovalRecord(
            approval_id=row.id,
            proposal_id=row.proposal_id,
            merchant_id=row.merchant_id,
            order_hash=row.order_hash,
            nonce=row.nonce,
            status=row.status,
            expires_at=row.expires_at,
        )


class DatabaseTransactionExecutor:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        approval_authority: DatabaseApprovalAuthority,
        suppliers: list[SupplierAdapter],
    ) -> None:
        self.session_factory = session_factory
        self.approval_authority = approval_authority
        self.suppliers = suppliers

    async def execute(
        self,
        proposal: PurchaseProposal,
        *,
        approval_id: UUID,
        approval_token: str,
        idempotency_key: str,
    ) -> OrderResult:
        from app.infrastructure.db.repositories.approvals import ApprovalRepository
        from app.infrastructure.db.repositories.orders import OrderRepository

        supplier = next(
            (
                item
                for item in self.suppliers
                if getattr(item, "supplier_id", None) == proposal.supplier_id
            ),
            None,
        )
        if supplier is None:
            supplier = next(
                (item for item in self.suppliers if getattr(item, "handles_all_suppliers", False)),
                None,
            )
        if supplier is None:
            raise AuthorizationError("No supplier adapter is registered for the approved supplier")
        async with self.session_factory() as session, session.begin():
            approvals = ApprovalRepository(session)
            approval_service = ApprovalService(
                approvals,
                secret=self.approval_authority.secret,
                algorithm=self.approval_authority.algorithm,
                ttl_minutes=self.approval_authority.ttl_minutes,
            )
            service = OrderService(
                session,
                approvals,
                OrderRepository(session),
                approval_service,
                supplier,
            )
            row = await service.execute(
                approval_id,
                merchant_id=proposal.merchant_id,
                approval_token=approval_token,
                idempotency_key=idempotency_key,
            )
            return OrderResult(
                order_id=row.id,
                status=row.status,
                supplier_confirmation=row.supplier_reference,
            )
