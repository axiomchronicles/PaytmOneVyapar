from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class A2AWebSocketHub:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, agent_id: UUID, socket: WebSocket) -> None:
        await socket.accept()
        self._connections[agent_id].add(socket)

    def disconnect(self, agent_id: UUID, socket: WebSocket) -> None:
        self._connections[agent_id].discard(socket)

    async def send(self, agent_id: UUID, message: dict) -> None:
        dead: list[WebSocket] = []
        for socket in self._connections[agent_id]:
            try:
                await socket.send_json(message)
            except RuntimeError:
                dead.append(socket)
        for socket in dead:
            self.disconnect(agent_id, socket)
