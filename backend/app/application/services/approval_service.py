import secrets
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.errors import AuthorizationError, ConflictError, StaleApprovalError
from app.core.security import (
    canonical_order_hash,
    create_approval_token,
    decode_token,
    utc_now,
)
from app.domain.entities import PurchaseProposal
from app.domain.enums import ApprovalStatus
from app.domain.events import EventType
from app.infrastructure.db.models import Approval, AuditLog, OutboxEvent
from app.infrastructure.db.repositories.approvals import ApprovalRepository


class ApprovalService:
    def __init__(
        self,
        repository: ApprovalRepository,
        *,
        secret: str,
        algorithm: str = "HS256",
        ttl_minutes: int = 10,
    ) -> None:
        self.repository = repository
        self.secret = secret
        self.algorithm = algorithm
        self.ttl_minutes = ttl_minutes

    async def create(
        self, proposal: PurchaseProposal, *, channel: str = "API"
    ) -> tuple[Approval, str]:
        payload = proposal.canonical_payload()
        order_hash = canonical_order_hash(payload)
        approval = Approval(
            merchant_id=proposal.merchant_id,
            proposal_id=proposal.proposal_id,
            order_hash=order_hash,
            proposal_payload=payload,
            status=ApprovalStatus.PENDING,
            nonce=secrets.token_urlsafe(24),
            expires_at=utc_now() + timedelta(minutes=self.ttl_minutes),
            channel=channel,
        )
        await self.repository.add(approval)
        self.repository.session.add(
            OutboxEvent(
                aggregate_type="approval",
                aggregate_id=approval.id,
                event_type=EventType.APPROVAL_REQUIRED,
                payload={"approval_id": str(approval.id), "order_hash": order_hash},
            )
        )
        self.repository.session.add(
            AuditLog(
                merchant_id=proposal.merchant_id,
                actor_type="AGENT",
                actor_id="purchase-workflow",
                action="approval.requested",
                resource_type="approval",
                resource_id=str(approval.id),
                metadata_={"order_hash": order_hash},
            )
        )
        token = self._token(approval)
        return approval, token

    async def approve(
        self, approval_id: UUID, *, merchant_id: UUID, user_id: UUID, token: str
    ) -> Approval:
        approval = await self.repository.get(approval_id, for_update=True)
        self._verify_owner_and_state(approval, merchant_id)
        self.verify_token(approval, token)
        approval.status = ApprovalStatus.APPROVED
        approval.decided_at = utc_now()
        approval.decided_by_user_id = user_id
        self.repository.session.add(
            OutboxEvent(
                aggregate_type="approval",
                aggregate_id=approval.id,
                event_type=EventType.APPROVAL_GRANTED,
                payload={"approval_id": str(approval.id), "order_hash": approval.order_hash},
            )
        )
        self._audit(approval, "approval.granted", str(user_id))
        await self.repository.session.flush()
        return approval

    async def reject(self, approval_id: UUID, *, merchant_id: UUID, user_id: UUID) -> Approval:
        approval = await self.repository.get(approval_id, for_update=True)
        self._verify_owner_and_state(approval, merchant_id)
        approval.status = ApprovalStatus.REJECTED
        approval.decided_at = utc_now()
        approval.decided_by_user_id = user_id
        self.repository.session.add(
            OutboxEvent(
                aggregate_type="approval",
                aggregate_id=approval.id,
                event_type=EventType.APPROVAL_REJECTED,
                payload={"approval_id": str(approval.id)},
            )
        )
        self._audit(approval, "approval.rejected", str(user_id))
        await self.repository.session.flush()
        return approval

    async def modify(
        self,
        approval_id: UUID,
        *,
        merchant_id: UUID,
        user_id: UUID,
        quantity: Decimal | None = None,
        max_unit_price: Decimal | None = None,
    ) -> tuple[Approval, str]:
        old = await self.repository.get(approval_id, for_update=True)
        self._verify_owner_and_state(old, merchant_id)
        old.status = ApprovalStatus.MODIFIED
        old.decided_at = utc_now()
        old.decided_by_user_id = user_id
        self._audit(old, "approval.modified", str(user_id))
        payload = old.proposal_payload
        revised = PurchaseProposal(
            proposal_id=uuid4(),
            merchant_id=merchant_id,
            store_id=payload["store_id"],
            supplier_id=payload["supplier_id"],
            sku=payload["sku"],
            quantity=quantity or Decimal(payload["quantity"]),
            unit=payload["unit"],
            unit_price=min(
                Decimal(payload["unit_price"]), max_unit_price or Decimal(payload["unit_price"])
            ),
            currency=payload["currency"],
            delivery_at=payload["delivery_at"],
            quote_id=payload["quote_id"],
        )
        return await self.create(revised, channel=old.channel)

    async def mark_modified(
        self, approval_id: UUID, *, merchant_id: UUID, user_id: UUID, token: str
    ) -> Approval:
        approval = await self.repository.get(approval_id, for_update=True)
        self._verify_owner_and_state(approval, merchant_id)
        self.verify_token(approval, token)
        approval.status = ApprovalStatus.MODIFIED
        approval.decided_at = utc_now()
        approval.decided_by_user_id = user_id
        self._audit(approval, "approval.modified", str(user_id))
        await self.repository.session.flush()
        return approval

    def verify_token(self, approval: Approval, token: str) -> None:
        claims = decode_token(token, secret=self.secret, algorithm=self.algorithm)
        expected = {
            "sub": str(approval.merchant_id),
            "proposal_id": str(approval.proposal_id),
            "approval_id": str(approval.id),
            "order_hash": approval.order_hash,
            "nonce": approval.nonce,
            "type": "approval",
        }
        if any(claims.get(key) != value for key, value in expected.items()):
            raise AuthorizationError("Approval token does not match the approved proposal")

    def _token(self, approval: Approval) -> str:
        return create_approval_token(
            merchant_id=approval.merchant_id,
            proposal_id=approval.proposal_id,
            approval_id=approval.id,
            order_hash=approval.order_hash,
            nonce=approval.nonce,
            secret=self.secret,
            algorithm=self.algorithm,
            ttl_minutes=self.ttl_minutes,
            expires_at=approval.expires_at,
        )

    def token_for(self, approval: Approval, *, merchant_id: UUID) -> str:
        if approval.merchant_id != merchant_id:
            raise AuthorizationError("Approval belongs to another merchant")
        return self._token(approval)

    def _audit(self, approval: Approval, action: str, actor_id: str) -> None:
        self.repository.session.add(
            AuditLog(
                merchant_id=approval.merchant_id,
                actor_type="USER",
                actor_id=actor_id,
                action=action,
                resource_type="approval",
                resource_id=str(approval.id),
                metadata_={"order_hash": approval.order_hash},
            )
        )

    @staticmethod
    def _verify_owner_and_state(approval: Approval, merchant_id: UUID) -> None:
        if approval.merchant_id != merchant_id:
            raise AuthorizationError("Approval belongs to another merchant")
        if approval.status != ApprovalStatus.PENDING:
            raise ConflictError(f"Approval is already {approval.status}")
        expires_at = approval.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=utc_now().tzinfo)
        if expires_at <= utc_now():
            approval.status = ApprovalStatus.EXPIRED
            raise StaleApprovalError("Approval has expired")
