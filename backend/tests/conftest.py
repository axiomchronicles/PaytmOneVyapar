import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Inventory, Merchant, Product, Store, User
from app.infrastructure.db.session import get_session
from app.main import create_app

MERCHANT_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
USER_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
STORE_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
PRODUCT_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
JWT_SECRET = "test-secret-that-is-longer-than-thirty-two-bytes"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+aiosqlite://",
        auth_jwt_secret=JWT_SECRET,
        auth_approval_secret=JWT_SECRET,
        whatsapp_verify_token="verify-me",
        whatsapp_app_secret="whatsapp-test-secret",
        telegram_bot_token="test-telegram-token",
        telegram_webhook_secret=None,
    )


@pytest.fixture
def db_factory(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session, session.begin():
            session.add_all(
                [
                    Merchant(
                        id=MERCHANT_ID,
                        name="Test Merchant",
                        phone_number="919000000000",
                        spending_limit=Decimal("50000"),
                    ),
                    User(
                        id=USER_ID,
                        merchant_id=MERCHANT_ID,
                        email="merchant@example.com",
                        password_hash=hash_password("correct-password"),
                        role="owner",
                    ),
                    Store(id=STORE_ID, merchant_id=MERCHANT_ID, name="Test Store"),
                    Product(
                        id=PRODUCT_ID,
                        merchant_id=MERCHANT_ID,
                        sku="COLD-COLA-300",
                        name="Cola crate",
                        unit="crate",
                    ),
                    Inventory(
                        merchant_id=MERCHANT_ID,
                        store_id=STORE_ID,
                        product_id=PRODUCT_ID,
                        quantity_on_hand=Decimal("3"),
                        reorder_point=Decimal("8"),
                    ),
                ]
            )

    asyncio.run(prepare())
    yield factory
    asyncio.run(engine.dispose())


@pytest.fixture
def client(settings: Settings, db_factory) -> TestClient:
    app = create_app(settings)

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with db_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(settings: Settings) -> dict[str, str]:
    token = create_access_token(
        subject=USER_ID,
        merchant_id=MERCHANT_ID,
        secret=settings.auth_jwt_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=30,
    )
    return {"Authorization": f"Bearer {token}"}


def workflow_state(*, spending_limit: float = 50000) -> dict:
    return {
        "merchant_id": str(MERCHANT_ID),
        "store_id": str(STORE_ID),
        "request_id": "test-purchase-request",
        "sku": "COLD-COLA-300",
        "required_quantity": 0,
        "unit": "crate",
        "target_price": 450,
        "max_price": 480,
        "spending_limit": spending_limit,
        "delivery_requirement": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "inventory_snapshot": {
            "quantity_on_hand": 3,
            "reorder_point": 8,
            "safety_stock": 2,
            "captured_at": datetime.now(UTC).isoformat(),
        },
        "sales_history": [
            {
                "date": (datetime.now(UTC) - timedelta(days=day)).isoformat(),
                "sales": 7 if day <= 7 else 4,
                "inventory": 20,
                "price": 600,
            }
            for day in range(28, 0, -1)
        ],
        "trace_id": "test-trace",
        "proposal_revision": 1,
        "attempted_supplier_ids": [],
    }
