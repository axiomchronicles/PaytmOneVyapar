from app.agents.registry import AgentDefinition

merchant_agent = AgentDefinition(
    name="merchant",
    responsibility="Interpret merchant intent and coordinate workflows without transactional mutation.",
    allowed_tools=("inventory.read", "workflow.start", "approval.request"),
)
