import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from conftest import MERCHANT_ID, STORE_ID
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.domain.entities import PurchaseRequest
from app.infrastructure.db.models import (
    Merchant,
    Order,
    OrderItem,
    Product,
    Supplier,
    SupplierProduct,
    User,
)
from app.integrations.suppliers.catalog_supplier import CatalogSupplierAdapter

SUPPLIER_MERCHANT_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
SUPPLIER_USER_ID = UUID("ffffffff-ffff-4fff-8fff-ffffffffffff")
SUPPLIER_ID = UUID("12121212-1212-4121-8121-121212121212")


def supplier_headers(settings) -> dict[str, str]:
    token = create_access_token(
        subject=SUPPLIER_USER_ID,
        merchant_id=SUPPLIER_MERCHANT_ID,
        secret=settings.auth_jwt_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=30,
        role="supplier",
    )
    return {"Authorization": f"Bearer {token}"}


def test_supplier_catalog_is_globally_discoverable_and_requires_supplier_confirmation(
    client, auth_headers, db_factory, settings
) -> None:
    async def prepare_supplier() -> None:
        async with db_factory() as session, session.begin():
            session.add_all(
                [
                    Merchant(
                        id=SUPPLIER_MERCHANT_ID,
                        name="Catalog Supplier",
                        phone_number="919123456789",
                        spending_limit=Decimal("100000"),
                        business_type="supplier",
                    ),
                    User(
                        id=SUPPLIER_USER_ID,
                        merchant_id=SUPPLIER_MERCHANT_ID,
                        email="catalog-supplier@example.com",
                        password_hash=hash_password("correct-password"),
                        role="supplier",
                    ),
                    Supplier(
                        id=SUPPLIER_ID,
                        merchant_id=SUPPLIER_MERCHANT_ID,
                        name="Catalog Supplier",
                        trust_score=Decimal("0.95"),
                        is_active=True,
                        city="Bengaluru",
                    ),
                ]
            )

    asyncio.run(prepare_supplier())
    supplier_auth = supplier_headers(settings)
    catalog = client.post(
        "/api/v1/suppliers/me/products",
        headers=supplier_auth,
        json={
            "sku": "COLD-COLA-300",
            "name": "Cola 300 ml crate",
            "unit": "crate",
            "available_quantity": 12,
            "unit_price": 450,
            "lead_time_days": 1,
            "category": "Cold drinks",
        },
    )
    assert catalog.status_code == 201, catalog.text
    assert Decimal(catalog.json()["available_quantity"]) == Decimal("12")

    # A radius that would previously filter the supplier must not hide it.
    discovery = client.get(
        "/api/v1/suppliers/discovery/nearby?radius_km=0",
        headers=auth_headers,
    )
    assert discovery.status_code == 200, discovery.text
    assert SUPPLIER_ID.__str__() in {row["id"] for row in discovery.json()["items"]}

    # The merchant dashboard uses this endpoint (not the discovery endpoint).
    dashboard_suppliers = client.get("/api/v1/suppliers", headers=auth_headers)
    assert dashboard_suppliers.status_code == 200, dashboard_suppliers.text
    assert SUPPLIER_ID.__str__() in {
        row["id"] for row in dashboard_suppliers.json()["items"]
    }

    async def add_pending_order() -> UUID:
        async with db_factory() as session, session.begin():
            product = await session.scalar(
                select(Product).where(
                    Product.merchant_id == SUPPLIER_MERCHANT_ID,
                    Product.sku == "COLD-COLA-300",
                )
            )
            assert product is not None
            order = Order(
                merchant_id=MERCHANT_ID,
                store_id=STORE_ID,
                supplier_id=SUPPLIER_ID,
                proposal_id=uuid4(),
                order_hash="a" * 64,
                status="APPROVAL_PENDING",
                currency="INR",
                total_amount=Decimal("900"),
                idempotency_key="supplier-portal-pending-order",
            )
            session.add(order)
            await session.flush()
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    sku="COLD-COLA-300",
                    quantity=Decimal("2"),
                    unit="crate",
                    unit_price=Decimal("450"),
                )
            )
            return order.id

    order_id = asyncio.run(add_pending_order())
    incoming = client.get("/api/v1/suppliers/me/orders", headers=supplier_auth)
    assert incoming.status_code == 200, incoming.text
    assert incoming.json()["items"][0]["status"] == "APPROVAL_PENDING"
    decision = client.post(
        f"/api/v1/suppliers/me/orders/{order_id}/decision",
        headers=supplier_auth,
        json={"approved": True, "idempotency_key": "supplier-portal-approve-1"},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "CONFIRMED"

    async def assert_stock_reserved() -> None:
        async with db_factory() as session:
            stock = await session.scalar(
                select(SupplierProduct.available_quantity).where(
                    SupplierProduct.supplier_id == SUPPLIER_ID
                )
            )
            assert stock == Decimal("10.000")

    asyncio.run(assert_stock_reserved())


def test_catalog_adapter_quotes_supplier_owned_stock(db_factory) -> None:
    async def run() -> None:
        async with db_factory() as session, session.begin():
            session.add_all(
                [
                    Merchant(
                        id=SUPPLIER_MERCHANT_ID,
                        name="Adapter Supplier",
                        phone_number="919123456780",
                        spending_limit=Decimal("100000"),
                    ),
                    Supplier(
                        id=SUPPLIER_ID,
                        merchant_id=SUPPLIER_MERCHANT_ID,
                        name="Adapter Supplier",
                        trust_score=Decimal("0.95"),
                        is_active=True,
                    ),
                    Product(
                        merchant_id=SUPPLIER_MERCHANT_ID,
                        sku="COLD-COLA-300",
                        name="Cola crate",
                        unit="crate",
                    ),
                ]
            )
            await session.flush()
            product = await session.scalar(
                select(Product).where(Product.merchant_id == SUPPLIER_MERCHANT_ID)
            )
            assert product is not None
            session.add(
                SupplierProduct(
                    supplier_id=SUPPLIER_ID,
                    product_id=product.id,
                    supplier_sku="SUP-COLA",
                    available_quantity=Decimal("30"),
                    unit_price=Decimal("449"),
                    lead_time_days=1,
                )
            )

        adapter = CatalogSupplierAdapter(db_factory)
        quotes = await adapter.discover(
            PurchaseRequest(
                request_id="catalog-adapter-test",
                merchant_id=MERCHANT_ID,
                store_id=STORE_ID,
                sku="COLD-COLA-300",
                quantity=Decimal("2"),
                unit="crate",
                target_price=Decimal("440"),
                max_price=Decimal("480"),
                delivery_deadline=datetime.now(UTC) + timedelta(days=2),
            )
        )
        assert [(quote.supplier_id, quote.unit_price) for quote in quotes] == [
            (SUPPLIER_ID, Decimal("449"))
        ]

    asyncio.run(run())
