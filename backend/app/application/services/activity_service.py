from typing import Any, Protocol
from uuid import UUID, uuid5

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.events import EventType
from app.infrastructure.db.models import A2AMessage, Negotiation, OutboxEvent

NEGOTIATION_NAMESPACE = UUID("c0ffee00-0000-4000-8000-000000000003")


class WorkflowActivityRecorder(Protocol):
    async def record_negotiation(self, state: dict[str, Any]) -> None: ...


class NullWorkflowActivityRecorder:
    async def record_negotiation(self, state: dict[str, Any]) -> None:
        return None


class DatabaseWorkflowActivityRecorder:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def record_negotiation(self, state: dict[str, Any]) -> None:
        merchant_id = UUID(state["merchant_id"])
        supplier = state.get("selected_supplier") or {}
        supplier_id = supplier.get("supplier_id")
        if not supplier_id:
            return
        correlation_id = UUID(
            state.get("negotiation_correlation_id")
            or str(uuid5(NEGOTIATION_NAMESPACE, state["request_id"]))
        )
        async with self.session_factory() as session, session.begin():
            row = await session.scalar(
                select(Negotiation).where(
                    Negotiation.merchant_id == merchant_id,
                    Negotiation.workflow_request_id == state["request_id"],
                )
            )
            if row is None:
                row = Negotiation(
                    merchant_id=merchant_id,
                    store_id=UUID(state["store_id"]),
                    supplier_id=UUID(str(supplier_id)),
                    correlation_id=correlation_id,
                    workflow_request_id=state["request_id"],
                    sku=state["sku"],
                    status=("ACCEPTED" if state.get("selected_supplier") else "FAILED"),
                    round_count=len(state.get("negotiation_history", [])),
                    constraints={
                        "target_price": str(state["target_price"]),
                        "max_price": str(state["max_price"]),
                        "quantity": str(state["required_quantity"]),
                        "unit": state["unit"],
                    },
                    history=state.get("negotiation_history", []),
                    current_quote=supplier or None,
                    proposal_id=(
                        UUID(state["proposal"]["proposal_id"])
                        if state.get("proposal", {}).get("proposal_id")
                        else None
                    ),
                )
                session.add(row)
                await session.flush()
            else:
                row.status = "ACCEPTED" if state.get("selected_supplier") else "FAILED"
                row.round_count = len(state.get("negotiation_history", []))
                row.history = state.get("negotiation_history", [])
                row.current_quote = supplier or None
                if state.get("proposal", {}).get("proposal_id"):
                    row.proposal_id = UUID(state["proposal"]["proposal_id"])
            await session.execute(
                update(A2AMessage)
                .where(
                    A2AMessage.merchant_id == merchant_id,
                    A2AMessage.correlation_id == correlation_id,
                )
                .values(negotiation_id=row.id)
            )
            session.add(
                OutboxEvent(
                    merchant_id=merchant_id,
                    aggregate_type="negotiation",
                    aggregate_id=row.id,
                    event_type=EventType.NEGOTIATION_UPDATED,
                    correlation_id=str(correlation_id),
                    payload={
                        "negotiation_id": str(row.id),
                        "status": row.status,
                        "supplier_id": str(row.supplier_id),
                    },
                )
            )


class DatabaseA2ARecorder:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def record(
        self,
        envelope,
        *,
        direction: str,
        merchant_id: UUID,
        supplier_id: UUID,
    ) -> None:
        async with self.session_factory() as session, session.begin():
            exists = await session.scalar(
                select(A2AMessage.id).where(
                    (A2AMessage.message_id == envelope.message_id)
                    | (A2AMessage.idempotency_key == envelope.idempotency_key)
                )
            )
            if exists is not None:
                return
            negotiation_id = await session.scalar(
                select(Negotiation.id).where(
                    Negotiation.merchant_id == merchant_id,
                    Negotiation.correlation_id == envelope.correlation_id,
                )
            )
            row = A2AMessage(
                merchant_id=merchant_id,
                supplier_id=supplier_id,
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
            session.add(row)
            await session.flush()
            session.add(
                OutboxEvent(
                    merchant_id=merchant_id,
                    aggregate_type="a2a_message",
                    aggregate_id=row.id,
                    event_type=EventType.A2A_MESSAGE_RECEIVED,
                    correlation_id=str(envelope.correlation_id),
                    trace_id=envelope.trace_id,
                    payload={
                        "activity_id": str(row.id),
                        "intent": str(envelope.intent),
                        "direction": direction,
                        "supplier_id": str(supplier_id),
                    },
                )
            )
