from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.approval_service import ApprovalService
from app.core.errors import AuthorizationError, ConflictError, StaleApprovalError
from app.core.security import canonical_order_hash, utc_now
from app.domain.contracts import SupplierAdapter
from app.domain.entities import PurchaseProposal
from app.domain.enums import ApprovalStatus, NotificationType, OrderStatus, TransactionStatus
from app.domain.events import EventType
from app.infrastructure.db.models import (
    A2AMessage,
    AuditLog,
    IdempotencyKey,
    Merchant,
    Negotiation,
    Notification,
    Order,
    OrderEvent,
    OrderItem,
    OutboxEvent,
    Transaction,
)
from app.infrastructure.db.repositories.approvals import ApprovalRepository
from app.infrastructure.db.repositories.orders import OrderRepository


class OrderService:
    def __init__(
        self,
        session: AsyncSession,
        approvals: ApprovalRepository,
        orders: OrderRepository,
        approval_service: ApprovalService,
        supplier: SupplierAdapter,
    ) -> None:
        self.session = session
        self.approvals = approvals
        self.orders = orders
        self.approval_service = approval_service
        self.supplier = supplier

    async def execute(
        self,
        approval_id: UUID,
        *,
        merchant_id: UUID,
        approval_token: str,
        idempotency_key: str,
    ) -> Order:
        request_correlation_id = idempotency_key.rsplit(":", 2)[0]
        existing = await self.orders.by_idempotency_key(merchant_id, idempotency_key)
        if existing:
            return existing
        approval = await self.approvals.get(approval_id, for_update=True)
        if approval.merchant_id != merchant_id:
            raise AuthorizationError("Approval belongs to another merchant")
        if approval.status != ApprovalStatus.APPROVED:
            raise ConflictError("Order execution requires an approved proposal")
        expires_at = approval.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=utc_now().tzinfo)
        if expires_at <= utc_now():
            raise StaleApprovalError("Approval expired before execution")
        self.approval_service.verify_token(approval, approval_token)
        if canonical_order_hash(approval.proposal_payload) != approval.order_hash:
            raise AuthorizationError("Approved order payload has changed")

        proposal = self._proposal(approval.proposal_payload)
        merchant = await self.session.scalar(select(Merchant).where(Merchant.id == merchant_id))
        if merchant is None:
            raise AuthorizationError("Merchant no longer exists")
        if proposal.total_amount > merchant.spending_limit:
            raise AuthorizationError("Order exceeds the merchant spending limit")

        idempotency = IdempotencyKey(
            scope=f"order:{merchant_id}",
            key=idempotency_key,
            request_hash=approval.order_hash,
        )
        self.session.add(idempotency)

        order = Order(
            merchant_id=merchant_id,
            store_id=proposal.store_id,
            supplier_id=proposal.supplier_id,
            proposal_id=proposal.proposal_id,
            approval_id=approval.id,
            order_hash=approval.order_hash,
            status=OrderStatus.EXECUTING,
            currency=proposal.currency,
            total_amount=proposal.total_amount,
            idempotency_key=idempotency_key,
        )
        await self.orders.add(order)
        self.session.add(
            OrderEvent(
                merchant_id=merchant_id,
                order_id=order.id,
                status=OrderStatus.EXECUTING,
                details={"approval_id": str(approval.id)},
            )
        )
        self.session.add(
            OrderItem(
                order_id=order.id,
                sku=proposal.sku,
                quantity=proposal.quantity,
                unit=proposal.unit,
                unit_price=proposal.unit_price,
            )
        )
        transaction = Transaction(
            merchant_id=merchant_id,
            order_id=order.id,
            approval_id=approval.id,
            amount=proposal.total_amount,
            currency=proposal.currency,
            status=TransactionStatus.PENDING,
            idempotency_key=idempotency_key,
        )
        self.session.add(transaction)
        await self.session.flush()

        try:
            result = await self.supplier.place_order(proposal, idempotency_key=idempotency_key)
        except Exception as exc:
            order.status = OrderStatus.FAILED
            order.failure_reason = type(exc).__name__
            transaction.status = TransactionStatus.FAILED
            transaction.error = {"type": type(exc).__name__}
            event_type = EventType.ORDER_FAILED
        else:
            order.status = result.status
            order.supplier_reference = result.supplier_confirmation
            transaction.status = TransactionStatus.SUCCEEDED
            transaction.provider_reference = result.supplier_confirmation
            event_type = EventType.ORDER_EXECUTED
        for envelope, direction, message_merchant_id in getattr(
            self.supplier, "pop_pending_messages", lambda _: []
        )(idempotency_key):
            negotiation_id = await self.session.scalar(
                select(Negotiation.id).where(
                    Negotiation.merchant_id == message_merchant_id,
                    Negotiation.correlation_id == envelope.correlation_id,
                )
            )
            message = A2AMessage(
                merchant_id=message_merchant_id,
                supplier_id=proposal.supplier_id,
                order_id=order.id,
                negotiation_id=negotiation_id,
                message_id=envelope.message_id,
                correlation_id=envelope.correlation_id,
                trace_id=envelope.trace_id,
                sender_agent_id=envelope.sender_agent_id,
                receiver_agent_id=envelope.receiver_agent_id,
                intent=envelope.intent,
                direction=direction,
                status="SENT" if direction == "OUTBOUND" else "RECEIVED",
                nonce=envelope.nonce,
                idempotency_key=envelope.idempotency_key,
                envelope=envelope.model_dump(mode="json"),
                expires_at=envelope.expires_at,
                processed_at=envelope.timestamp,
            )
            self.session.add(message)
            await self.session.flush()
            self.session.add(
                OutboxEvent(
                    merchant_id=message_merchant_id,
                    aggregate_type="a2a_message",
                    aggregate_id=message.id,
                    event_type=EventType.A2A_MESSAGE_RECEIVED,
                    correlation_id=str(envelope.correlation_id),
                    trace_id=envelope.trace_id,
                    payload={
                        "activity_id": str(message.id),
                        "intent": str(envelope.intent),
                        "direction": direction,
                        "supplier_id": str(proposal.supplier_id),
                        "order_id": str(order.id),
                    },
                )
            )
        idempotency.status = "COMPLETED"
        idempotency.response = {"order_id": str(order.id), "status": order.status}
        self.session.add(
            OutboxEvent(
                merchant_id=merchant_id,
                aggregate_type="order",
                aggregate_id=order.id,
                event_type=event_type,
                correlation_id=request_correlation_id,
                payload={"order_id": str(order.id), "status": order.status},
            )
        )
        self.session.add(
            OrderEvent(
                merchant_id=merchant_id,
                order_id=order.id,
                status=order.status,
                details={
                    "supplier_reference": order.supplier_reference,
                    "failure_reason": order.failure_reason,
                },
            )
        )
        notification = Notification(
            merchant_id=merchant_id,
            notification_type=NotificationType.ORDER_UPDATE,
            title=("Order confirmed" if order.status == OrderStatus.CONFIRMED else "Order failed"),
            body=(
                "Your supplier confirmed the purchase order."
                if order.status == OrderStatus.CONFIRMED
                else "The supplier could not complete the purchase order."
            ),
            entity_type="order",
            entity_id=order.id,
            payload={"status": order.status},
        )
        self.session.add(notification)
        await self.session.flush()
        a2a_correlation_id = getattr(self.supplier, "correlation_id_for_quote", lambda _: None)(
            proposal.quote_id
        )
        if a2a_correlation_id is not None:
            await self.session.execute(
                update(A2AMessage)
                .where(
                    A2AMessage.merchant_id == merchant_id,
                    A2AMessage.correlation_id == a2a_correlation_id,
                )
                .values(order_id=order.id)
            )
        self.session.add(
            OutboxEvent(
                merchant_id=merchant_id,
                aggregate_type="notification",
                aggregate_id=notification.id,
                event_type=EventType.NOTIFICATION_CREATED,
                correlation_id=request_correlation_id,
                payload={
                    "notification_id": str(notification.id),
                    "notification_type": notification.notification_type,
                    "entity_type": "order",
                    "entity_id": str(order.id),
                },
            )
        )
        self.session.add(
            AuditLog(
                merchant_id=merchant_id,
                actor_type="TRANSACTION_SERVICE",
                actor_id="order-executor",
                action="order.executed"
                if order.status == OrderStatus.CONFIRMED
                else "order.failed",
                resource_type="order",
                resource_id=str(order.id),
                metadata_={
                    "approval_id": str(approval.id),
                    "order_hash": approval.order_hash,
                    "status": order.status,
                },
            )
        )
        await self.session.flush()
        return order

    @staticmethod
    def _proposal(payload: dict) -> PurchaseProposal:
        return PurchaseProposal(
            proposal_id=payload["proposal_id"],
            merchant_id=payload["merchant_id"],
            store_id=payload["store_id"],
            supplier_id=payload["supplier_id"],
            sku=payload["sku"],
            quantity=Decimal(payload["quantity"]),
            unit=payload["unit"],
            unit_price=Decimal(payload["unit_price"]),
            currency=payload["currency"],
            delivery_at=datetime.fromisoformat(payload["delivery_at"]),
            quote_id=payload["quote_id"],
        )
