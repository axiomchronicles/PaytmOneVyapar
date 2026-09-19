import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.v1.voice import _websocket_principal

router = APIRouter(tags=["realtime"])


class RealtimeHub:
    def __init__(self) -> None:
        self.connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, merchant_id: UUID, socket: WebSocket) -> None:
        await socket.accept()
        self.connections[merchant_id].add(socket)

    def disconnect(self, merchant_id: UUID, socket: WebSocket) -> None:
        self.connections[merchant_id].discard(socket)

    async def publish(self, merchant_id: UUID, event: dict) -> None:
        stale = []
        for socket in tuple(self.connections[merchant_id]):
            try:
                await socket.send_json(event)
            except Exception:
                stale.append(socket)
        for socket in stale:
            self.disconnect(merchant_id, socket)


@router.websocket("/ws")
async def events(websocket: WebSocket) -> None:
    try:
        authorization = websocket.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            token = websocket.query_params.get("token", "")
        if not token:
            raise ValueError("Missing bearer token")
        principal = await _websocket_principal(websocket, token, websocket.app.state.settings)
    except Exception:
        await websocket.accept()
        await websocket.close(code=4401, reason="Unauthorized")
        return
    hub: RealtimeHub = websocket.app.state.realtime_hub
    await hub.connect(principal.merchant_id, websocket)
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=25)
            except TimeoutError:
                await websocket.send_json({"type": "HEARTBEAT"})
                continue
            if message == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        hub.disconnect(principal.merchant_id, websocket)

