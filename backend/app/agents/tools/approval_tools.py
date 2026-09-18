from app.core.security import canonical_order_hash
from app.domain.entities import PurchaseProposal


def proposal_hash(proposal: PurchaseProposal) -> str:
    return canonical_order_hash(proposal.canonical_payload())
