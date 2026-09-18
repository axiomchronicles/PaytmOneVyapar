import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import VoiceSessionRequest
from app.channels.voice.protocol import VoiceEventType
from app.channels.voice.session import VoiceSession
from app.core.config import Settings, get_settings
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import AuthenticationError, NotFoundError
from app.infrastructure.db.models import User
from app.infrastructure.db.models import VoiceSession as VoiceSessionRow
from app.infrastructure.db.session import get_session, get_session_factory

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/sessions", status_code=201)
async def create_voice_session(
    body: VoiceSessionRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_session),
) -> dict:
    session = VoiceSession(
        merchant_id=principal.merchant_id,
        user_id=principal.user_id,
        language_code=body.language_code,
        sample_rate=body.sample_rate,
        encoding=body.encoding,
        active_proposal_id=body.active_proposal_id,
        active_request_id=body.active_request_id,
        approval_token=body.approval_token,
    )
    request.app.state.voice_sessions[session.session_id] = session
    db.add(
        VoiceSessionRow(
            id=session.session_id,
            merchant_id=session.merchant_id,
            user_id=session.user_id,
            active_proposal_id=session.active_proposal_id,
            language_code=session.language_code,
            status="ACTIVE",
            started_at=session.started_at,
            audio_metadata={
                "encoding": session.encoding,
                "sample_rate": session.sample_rate,
                "channels": 1,
            },
        )
    )
    await db.commit()
    return {
        "session_id": session.session_id,
        "stream_url": f"/api/v1/voice/sessions/{session.session_id}/stream",
        "provider_available": request.app.state.voice_pipeline is not None,
        "audio": {
            "encoding": session.encoding,
            "sample_rate": session.sample_rate,
            "channels": 1,
        },
    }


async def _websocket_principal(websocket: WebSocket, token: str, settings: Settings) -> Principal:
    try:
        claims = jwt.decode(
            token,
            settings.auth_jwt_secret.get_secret_value(),
            algorithms=[settings.auth_jwt_algorithm],
        )
        user_id = UUID(claims["sub"])
        merchant_id = UUID(claims["merchant_id"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthenticationError("Invalid WebSocket token") from exc
    async with get_session_factory()() as db:
        user = await db.get(User, user_id)
        if user is None or not user.is_active or user.merchant_id != merchant_id:
            raise AuthenticationError("Inactive voice session user")
    return Principal(user_id=user_id, merchant_id=merchant_id, role=claims.get("role", "merchant"))


@router.websocket("/sessions/{session_id}/stream")
async def stream_voice(
    websocket: WebSocket,
    session_id: UUID,
) -> None:
    settings = get_settings()
    try:
        authorization = websocket.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthenticationError("Missing WebSocket bearer token")
        principal = await _websocket_principal(websocket, token, settings)
        session = websocket.app.state.voice_sessions.get(session_id)
        if session is None or session.merchant_id != principal.merchant_id:
            raise NotFoundError("Voice session not found")
        if session.closed:
            session.reconnect()
    except Exception:
        await websocket.close(code=4401)
        return
    pipeline = websocket.app.state.voice_pipeline
    if pipeline is None:
        await websocket.accept()
        await websocket.send_json(
            {"type": VoiceEventType.ERROR, "text": "Sarvam voice integration is not configured"}
        )
        await websocket.close(code=1011)
        return

    await websocket.accept()
    queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=32)

    async def audio() -> AsyncIterator[bytes]:
        while True:
            chunk = await queue.get()
            if chunk is None:
                return
            yield chunk

    async def produce() -> None:
        try:
            async for event in pipeline.run(session, audio()):
                if event.audio:
                    await websocket.send_bytes(event.audio)
                else:
                    await websocket.send_json(event.model_dump(mode="json", exclude_none=True))
        except Exception as exc:
            await websocket.send_json(
                {
                    "type": VoiceEventType.ERROR,
                    "text": "Voice provider failed",
                    "code": type(exc).__name__,
                }
            )

    producer = asyncio.create_task(produce())
    try:
        while True:
            message = await websocket.receive()
            if message.get("bytes") is not None:
                await queue.put(message["bytes"])
                continue
            if message.get("text"):
                control = json.loads(message["text"])
                if control.get("type") == "interrupt":
                    session.interrupt()
                elif control.get("type") == "end":
                    await queue.put(None)
                    break
                elif control.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await queue.put(None)
    finally:
        try:
            await asyncio.wait_for(producer, timeout=5)
        except Exception:
            producer.cancel()
            await asyncio.gather(producer, return_exceptions=True)
