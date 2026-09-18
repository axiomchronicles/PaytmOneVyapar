import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.infrastructure.db.models import (
    A2AAgent,
    Inventory,
    Merchant,
    Product,
    Sale,
    Store,
    Supplier,
    SupplierProduct,
    User,
)
from app.infrastructure.db.session import get_session_factory
from app.integrations.suppliers.mock_supplier import (
    BUYER_AGENT_ID,
    MockSupplierAdapter,
)

SEED_NAMESPACE = UUID("c0ffee00-0000-4000-8000-000000000003")
MERCHANT_ID = uuid5(SEED_NAMESPACE, "demo-merchant")
STORE_ID = uuid5(SEED_NAMESPACE, "demo-store")
USER_ID = uuid5(SEED_NAMESPACE, "demo-user")
PRODUCT_ID = uuid5(SEED_NAMESPACE, "cold-cola-300")


async def seed(session: AsyncSession) -> None:
    supplier = MockSupplierAdapter()
    rows = [
        Merchant(
            id=MERCHANT_ID,
            name="Sharma General Store",
            phone_number="919999999999",
            currency="INR",
            spending_limit=Decimal("50000"),
            settings={"demo": True},
        ),
        User(
            id=USER_ID,
            merchant_id=MERCHANT_ID,
            email="merchant@vyapaar.local",
            password_hash=hash_password("demo-change-me"),
            role="owner",
            is_email_verified=True,
            is_phone_verified=True,
        ),
        Store(
            id=STORE_ID,
            merchant_id=MERCHANT_ID,
            name="Indiranagar Store",
            timezone="Asia/Kolkata",
            address={"city": "Bengaluru", "postal_code": "560038"},
        ),
        Product(
            id=PRODUCT_ID,
            merchant_id=MERCHANT_ID,
            sku="COLD-COLA-300",
            name="Cola 300 ml crate",
            unit="crate",
            category="cold-drinks",
            attributes={"units_per_crate": 24},
        ),
        Inventory(
            id=uuid5(SEED_NAMESPACE, "demo-inventory"),
            merchant_id=MERCHANT_ID,
            store_id=STORE_ID,
            product_id=PRODUCT_ID,
            quantity_on_hand=Decimal("3"),
            reorder_point=Decimal("8"),
        ),
        Supplier(
            id=supplier.supplier_id,
            merchant_id=MERCHANT_ID,
            name=supplier.name,
            adapter_type="mock-a2a",
            trust_score=Decimal("0.98"),
            configuration={"deterministic": True},
        ),
        SupplierProduct(
            id=uuid5(SEED_NAMESPACE, "supplier-cold-cola"),
            supplier_id=supplier.supplier_id,
            product_id=PRODUCT_ID,
            supplier_sku="BWW-COLA-300-24",
            available_quantity=Decimal("240"),
            unit_price=Decimal("470"),
            lead_time_days=1,
        ),
        A2AAgent(
            id=BUYER_AGENT_ID,
            name="vyapaar-buyer-agent",
            endpoint="http://localhost:8000/api/v1/a2a/messages",
            shared_secret_ref="env:A2A_SIGNING_SECRET",
            allowed_intents=["PURCHASE_REQUEST", "COUNTER_OFFER", "OFFER_ACCEPTED"],
        ),
        A2AAgent(
            id=supplier.supplier_id,
            name="bharat-beverage-mock-agent",
            endpoint="http://localhost:8000/api/v1/a2a/mock-supplier/messages",
            shared_secret_ref="env:A2A_SIGNING_SECRET",
            supplier_id=supplier.supplier_id,
            allowed_intents=["QUOTE", "OFFER_REJECTED", "ORDER_CONFIRMATION"],
        ),
    ]
    for row in rows:
        await session.merge(row)

    today = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
    for days_ago in range(90, 0, -1):
        sold_at = today - timedelta(days=days_ago)
        weekend = sold_at.weekday() >= 5
        festival = days_ago in {7, 35, 70}
        hot = days_ago < 21
        quantity = 3 + int(weekend) * 2 + int(festival) * 3 + int(hot) * 2
        await session.merge(
            Sale(
                id=uuid5(SEED_NAMESPACE, f"sale:{sold_at.date()}"),
                merchant_id=MERCHANT_ID,
                store_id=STORE_ID,
                product_id=PRODUCT_ID,
                quantity=Decimal(quantity),
                unit_price=Decimal("600"),
                sold_at=sold_at,
                signals={
                    "festival_flag": festival,
                    "temperature_c": 34 if hot else 28,
                    "local_event_flag": days_ago in {5, 19},
                    "promotion_flag": False,
                },
            )
        )


async def main() -> None:
    async with get_session_factory()() as session, session.begin():
        await seed(session)
    print("Seeded merchant@vyapaar.local with the deterministic cold-drink scenario.")


if __name__ == "__main__":
    asyncio.run(main())
