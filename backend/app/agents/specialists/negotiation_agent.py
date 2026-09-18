from app.agents.registry import AgentDefinition

negotiation_agent = AgentDefinition(
    name="negotiation",
    responsibility="Negotiate only within merchant price, quantity, supplier, time, and round limits.",
    allowed_tools=("supplier.counter_offer", "constraints.validate"),
)
