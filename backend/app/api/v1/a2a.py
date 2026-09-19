from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.a2a.registry import AgentRegistry, RegisteredAgent
from app.a2a.schemas import A2AEnvelope, A2AIntent
from app.a2a.service import A2AService
from app.api.pagination import decode_cursor, next_cursor
from app.api.v1.business_schemas import A2AActivityView, CursorPage
from app.core.config import Settings, get_settings
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import AuthenticationError, NotFoundError
from app.domain.events import EventType
from app.infrastructure.db.models import A2AAgent, A2AMessage, Negotiation, OutboxEvent
from app.infrastructure.db.repositories.a2a import SQLA2AMessageRepository
from app.infrastructure.db.session import get_session, get_session_factory

router = APIRouter(prefix="/a2a", tags=["a2a"])

_SUMMARIES = {
    "PURCHASE_REQUEST": "Purchase request sent",
    "QUOTE": "Supplier quote received",
    "COUNTER_OFFER": "Counter offer sent",
    "OFFER_ACCEPTED": "Supplier offer accepted",
    "OFFER_REJECTED": "Supplier offer rejected",
    "ORDER_CONFIRMATION": "Order confirmation received",
    "DELIVERY_CONFIRMATION": "Delivery confirmed",
    "CANCELLATION": "Order or quote cancelled",
    "INVENTORY_SHORTAGE_ALERT": "Inventory shortage reported",
}


def _activity(row: A2AMessage) -> A2AActivityView:
    payload: dict[str, Any] = {}
    if row.envelope and isinstance(row.envelope, dict):
        payload = row.envelope.get("payload") or {}
    return A2AActivityView(
        id=row.id,
        message_id=row.message_id,
        correlation_id=row.correlation_id,
        supplier_id=row.supplier_id,
        order_id=row.order_id,
        negotiation_id=row.negotiation_id,
        intent=row.intent,
        direction=row.direction,
        status=row.status,
        summary=_SUMMARIES.get(row.intent, row.intent.replace("_", " ").title()),
        occurred_at=row.processed_at or row.created_at,
        payload=payload,
    )


@router.get("/activity", response_model=CursorPage[A2AActivityView])
async def list_activity(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    supplier_id: Annotated[UUID | None, Query()] = None,
    order_id: Annotated[UUID | None, Query()] = None,
    negotiation_id: Annotated[UUID | None, Query()] = None,
    intent: Annotated[A2AIntent | None, Query()] = None,
    status: Annotated[str | None, Query(max_length=40)] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> CursorPage[A2AActivityView]:
    query = select(A2AMessage).where(A2AMessage.merchant_id == principal.merchant_id)
    if supplier_id:
        query = query.where(A2AMessage.supplier_id == supplier_id)
    if order_id:
        query = query.where(A2AMessage.order_id == order_id)
    if negotiation_id:
        negotiation = await session.scalar(
            select(Negotiation).where(
                Negotiation.id == negotiation_id,
                Negotiation.merchant_id == principal.merchant_id,
            )
        )
        if negotiation is None:
            raise NotFoundError("Negotiation not found")
        query = query.where(A2AMessage.correlation_id == negotiation.correlation_id)
    if intent:
        query = query.where(A2AMessage.intent == intent)
    if status:
        query = query.where(A2AMessage.status == status)
    if created_from:
        query = query.where(A2AMessage.created_at >= created_from)
    if created_to:
        query = query.where(A2AMessage.created_at < created_to)
    if decoded := decode_cursor(cursor):
        created_at, row_id = decoded
        query = query.where(
            or_(
                A2AMessage.created_at < created_at,
                and_(A2AMessage.created_at == created_at, A2AMessage.id < row_id),
            )
        )
    rows = list(
        await session.scalars(
            query.order_by(A2AMessage.created_at.desc(), A2AMessage.id.desc()).limit(limit + 1)
        )
    )
    return CursorPage(
        items=[_activity(row) for row in rows[:limit]],
        next_cursor=next_cursor(rows, limit),
    )


@router.get("/conversations/{correlation_id}", response_model=list[A2AActivityView])
async def conversation(
    correlation_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[A2AActivityView]:
    rows = list(
        await session.scalars(
            select(A2AMessage)
            .where(
                A2AMessage.merchant_id == principal.merchant_id,
                A2AMessage.correlation_id == correlation_id,
            )
            .order_by(A2AMessage.created_at, A2AMessage.id)
            .limit(limit)
        )
    )
    if not rows:
        # A catalog-backed supplier may complete a deterministic quote without
        # generating a signed envelope.  Its negotiation is still real and
        # authorized; return an empty trail rather than a misleading 404.
        negotiation = await session.scalar(
            select(Negotiation.id).where(
                Negotiation.merchant_id == principal.merchant_id,
                Negotiation.correlation_id == correlation_id,
            )
        )
        if negotiation is not None:
            return []
        raise NotFoundError("A2A conversation not found")
    return [_activity(row) for row in rows]


@router.post("/messages", status_code=202)
async def receive_message(
    envelope: A2AEnvelope,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    registered = await session.scalar(
        select(A2AAgent).where(
            A2AAgent.id == envelope.sender_agent_id,
            A2AAgent.is_active.is_(True),
        )
    )
    if registered is None:
        raise AuthenticationError("A2A sender is not registered")
    registry = AgentRegistry(
        [
            RegisteredAgent(
                agent_id=envelope.sender_agent_id,
                name=registered.name,
                endpoint=registered.endpoint,
                signing_secret=settings.a2a_signing_secret.get_secret_value(),
                allowed_intents=frozenset(registered.allowed_intents),
            )
        ]
    )
    service = A2AService(
        registry=registry,
        repository=SQLA2AMessageRepository(session),
        receiver_id=str(settings.a2a_agent_id),
        max_clock_skew_seconds=settings.a2a_max_clock_skew_seconds,
    )
    payload = await service.receive(envelope)
    stored = await session.scalar(
        select(A2AMessage).where(A2AMessage.message_id == envelope.message_id)
    )
    merchant_id = getattr(payload, "merchant_id", None)
    if merchant_id is None:
        merchant_id = await session.scalar(
            select(A2AMessage.merchant_id)
            .where(
                A2AMessage.correlation_id == envelope.correlation_id,
                A2AMessage.merchant_id.is_not(None),
            )
            .order_by(A2AMessage.created_at)
            .limit(1)
        )
    if stored is not None and merchant_id is not None:
        stored.merchant_id = merchant_id
        stored.supplier_id = registered.supplier_id
        session.add(
            OutboxEvent(
                merchant_id=merchant_id,
                aggregate_type="a2a_message",
                aggregate_id=stored.id,
                event_type=EventType.A2A_MESSAGE_RECEIVED,
                correlation_id=str(envelope.correlation_id),
                trace_id=envelope.trace_id,
                payload={
                    "activity_id": str(stored.id),
                    "intent": str(envelope.intent),
                    "direction": "INBOUND",
                },
            )
        )
    await session.commit()
    return {"accepted": True, "message_id": envelope.message_id, "intent": payload.intent}


@router.post("/mock-supplier/messages")
async def mock_supplier_message(envelope: A2AEnvelope, request: Request) -> A2AEnvelope:
    return await request.app.state.mock_supplier.handle_envelope(envelope)


@router.get("/mock-supplier/inventory")
async def mock_supplier_inventory(request: Request) -> list[dict[str, str]]:
    return request.app.state.mock_supplier.advertised_inventory()


@router.websocket("/ws/{agent_id}")
async def a2a_stream(websocket: WebSocket, agent_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            envelope = A2AEnvelope.model_validate(await websocket.receive_json())
            if str(envelope.sender_agent_id) != agent_id:
                await websocket.close(code=4403)
                return
            settings = websocket.app.state.settings
            async with get_session_factory()() as session, session.begin():
                registered = await session.scalar(
                    select(A2AAgent).where(
                        A2AAgent.id == envelope.sender_agent_id,
                        A2AAgent.is_active.is_(True),
                    )
                )
                if registered is None:
                    await websocket.close(code=4401)
                    return
                service = A2AService(
                    registry=AgentRegistry(
                        [
                            RegisteredAgent(
                                agent_id=registered.id,
                                name=registered.name,
                                endpoint=registered.endpoint,
                                signing_secret=settings.a2a_signing_secret.get_secret_value(),
                                allowed_intents=frozenset(registered.allowed_intents),
                            )
                        ]
                    ),
                    repository=SQLA2AMessageRepository(session),
                    receiver_id=str(settings.a2a_agent_id),
                    max_clock_skew_seconds=settings.a2a_max_clock_skew_seconds,
                )
                await service.receive(envelope)
            await websocket.send_json({"type": "A2A_EVENT", "message_id": str(envelope.message_id)})
    except WebSocketDisconnect:
        return
