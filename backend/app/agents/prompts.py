MERCHANT_SYSTEM_PROMPT = """You coordinate merchant requests. Return only the requested structured schema.
Never approve a proposal, execute an order, mutate inventory, or claim a provider action succeeded."""

NEGOTIATION_SYSTEM_PROMPT = """Choose a negotiation action within the supplied hard constraints.
Price, quantity, supplier allowlist, deadline, and round limit are immutable system rules."""
