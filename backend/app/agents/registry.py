from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    responsibility: str
    allowed_tools: tuple[str, ...]


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, definition: AgentDefinition) -> None:
        if definition.name in self._agents:
            raise ValueError(f"Agent {definition.name} is already registered")
        self._agents[definition.name] = definition

    def get(self, name: str) -> AgentDefinition:
        return self._agents[name]

    def all(self) -> tuple[AgentDefinition, ...]:
        return tuple(self._agents.values())
