from app.agents.registry import AgentDefinition

procurement_agent = AgentDefinition(
    name="procurement",
    responsibility="Discover suppliers, compare offers, and construct purchase proposals.",
    allowed_tools=("supplier.discover", "supplier.quote", "proposal.create"),
)
