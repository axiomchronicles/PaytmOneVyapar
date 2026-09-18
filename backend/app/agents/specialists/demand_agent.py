from app.agents.registry import AgentDefinition

demand_agent = AgentDefinition(
    name="demand",
    responsibility="Produce structured demand and shortage forecasts from business data.",
    allowed_tools=("sales.read", "inventory.read", "forecast.predict"),
)
