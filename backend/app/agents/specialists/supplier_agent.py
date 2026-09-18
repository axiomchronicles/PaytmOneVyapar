from app.agents.registry import AgentDefinition

supplier_agent = AgentDefinition(
    name="supplier",
    responsibility="Respond to supplier-side quote, negotiation, order, and confirmation messages.",
    allowed_tools=("catalog.read", "quote.create", "order.confirm"),
)
