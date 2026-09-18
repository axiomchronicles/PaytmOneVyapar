from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.a2a.registry import AgentRegistry, RegisteredAgent
from app.a2a.schemas import A2AEnvelope
from app.a2a.service import A2AService
from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError
from app.infrastructure.db.models import A2AAgent
from app.infrastructure.db.repositories.a2a import SQLA2AMessageRepository
from app.infrastructure.db.session import get_session, get_session_factory

router = APIRouter(prefix="/a2a", tags=["a2a"])


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
