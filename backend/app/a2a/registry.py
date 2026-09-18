from dataclasses import dataclass, field
from uuid import UUID

from app.core.errors import AuthenticationError, NotFoundError


@dataclass(frozen=True)
class RegisteredAgent:
    agent_id: UUID
    name: str
    endpoint: str
    signing_secret: str
    active: bool = True
    allowed_intents: frozenset[str] = field(default_factory=frozenset)


class AgentRegistry:
    def __init__(self, agents: list[RegisteredAgent] | None = None) -> None:
        self._agents = {agent.agent_id: agent for agent in agents or []}

    def register(self, agent: RegisteredAgent) -> None:
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: UUID) -> RegisteredAgent:
        try:
            agent = self._agents[agent_id]
        except KeyError as exc:
            raise NotFoundError("A2A agent is not registered") from exc
        if not agent.active:
            raise AuthenticationError("A2A agent is disabled")
        return agent

    def authorize_intent(self, agent_id: UUID, intent: str) -> RegisteredAgent:
        agent = self.get(agent_id)
        if agent.allowed_intents and intent not in agent.allowed_intents:
            raise AuthenticationError("A2A sender is not permitted to use this intent")
        return agent
