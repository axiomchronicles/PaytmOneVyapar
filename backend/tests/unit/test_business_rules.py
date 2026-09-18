from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from app.application.services.negotiation_service import NegotiationConstraints, NegotiationService
from app.application.services.recommendation_service import (
    RecommendationCandidate,
    RecommendationService,
)
from app.application.services.risk_service import RiskService
from app.core.security import utc_now
from app.domain.entities import InventorySnapshot, PurchaseProposal, PurchaseRequest, SupplierQuote


def business_objects():
    supplier_id = uuid4()
    quote = SupplierQuote(
        supplier_id=supplier_id,
        supplier_name="Supplier",
        sku="COLA",
        available_quantity=10,
        unit_price=500,
        delivery_at=utc_now() + timedelta(days=1),
        quote_id="quote-1",
        expires_at=utc_now() + timedelta(minutes=10),
    )
    request = PurchaseRequest(
        sku="COLA",
        quantity=4,
        unit="crate",
        target_price=450,
        max_price=480,
        delivery_deadline=utc_now() + timedelta(days=2),
        merchant_id=uuid4(),
        store_id=uuid4(),
    )
    return supplier_id, quote, request


def test_negotiation_enforces_price_and_round_limits() -> None:
    supplier_id, quote, request = business_objects()
    constraints = NegotiationConstraints(
        min_quantity=1,
        max_quantity=10,
        max_unit_price=480,
        allowed_supplier_ids=frozenset({str(supplier_id)}),
        max_rounds=2,
    )
    accepted, failures = NegotiationService().validate_offer(
        quote, request, constraints, round_number=3
    )
    assert not accepted
    assert {"price_limit", "round_limit"} <= set(failures)


def test_risk_rejects_spending_limit_and_duplicate() -> None:
    _, quote, request = business_objects()
    proposal = PurchaseProposal(
        proposal_id=uuid4(),
        merchant_id=request.merchant_id,
        store_id=request.store_id,
        supplier_id=quote.supplier_id,
        sku=request.sku,
        quantity=4,
        unit="crate",
        unit_price=quote.unit_price,
        delivery_at=quote.delivery_at,
        quote_id=quote.quote_id,
    )
    result = RiskService().evaluate(
        inventory=InventorySnapshot(
            sku="COLA", quantity_on_hand=1, reorder_point=5, captured_at=utc_now()
        ),
        proposal=proposal,
        quote=quote,
        spending_limit=Decimal("100"),
        duplicate_order=True,
    )
    assert not result.passed
    assert {"spending_limit", "not_duplicate"} <= set(result.reasons)


def test_recommendations_are_stably_feature_ranked() -> None:
    candidates = [
        RecommendationCandidate("B", 0.2, 0.2, 0.2, 1),
        RecommendationCandidate("A", 1, 0.8, 0.5, 1),
    ]
    ranked = RecommendationService().rank(candidates)
    assert [item["sku"] for item in ranked] == ["A", "B"]
