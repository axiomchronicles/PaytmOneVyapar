from app.agents.registry import AgentDefinition

risk_agent = AgentDefinition(
    name="risk",
    responsibility="Evaluate anomalies, duplicates, trust, approval state, and spending limits.",
    allowed_tools=("risk.evaluate", "orders.read", "approvals.read"),
)
