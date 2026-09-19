import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import canonical_order_hash, hash_password
from app.domain.enums import ApprovalStatus
from app.infrastructure.db.models import (
    A2AAgent,
    A2AMessage,
    Approval,
    Customer,
    Inventory,
    Merchant,
    Negotiation,
    Notification,
    Order,
    OrderItem,
    Product,
    Sale,
    Settlement,
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

# Merchant 1 (Sharma General Store, Bengaluru)
SHARMA_MERCHANT_ID = uuid5(SEED_NAMESPACE, "demo-merchant")
SHARMA_USER_ID = uuid5(SEED_NAMESPACE, "demo-user")
SHARMA_STORE_ID = uuid5(SEED_NAMESPACE, "demo-store")

# Merchant 2 (Gupta Provision Store, Delhi)
GUPTA_MERCHANT_ID = uuid5(SEED_NAMESPACE, "gupta-merchant")
GUPTA_USER_ID = uuid5(SEED_NAMESPACE, "gupta-user")
GUPTA_STORE_ID = uuid5(SEED_NAMESPACE, "gupta-store")

# Supplier 1 (Bengaluru FMCG Hub)
SUPPLIER_MERCHANT_ID = uuid5(SEED_NAMESPACE, "supplier-merchant-hub")
SUPPLIER_USER_ID = uuid5(SEED_NAMESPACE, "supplier-user")
BENGALURU_HUB_SUPPLIER_ID = uuid5(SEED_NAMESPACE, "bengaluru-fmcg-supplier")

# Additional Suppliers
METRO_SUPPLIER_ID = uuid5(SEED_NAMESPACE, "metro-wholesale")
DELHI_SUPPLIER_ID = uuid5(SEED_NAMESPACE, "delhi-north-fmcg")

# Products
PROD_COLA = uuid5(SEED_NAMESPACE, "cold-cola-300")
PROD_TATA_SALT = uuid5(SEED_NAMESPACE, "tata-salt-1kg")
PROD_FORTUNE_OIL = uuid5(SEED_NAMESPACE, "fortune-oil-1l")
PROD_ATTA = uuid5(SEED_NAMESPACE, "aashirvaad-atta-5kg")
PROD_MAGGI = uuid5(SEED_NAMESPACE, "maggi-70g")
PROD_PARLE_G = uuid5(SEED_NAMESPACE, "parle-g-100g")
PROD_AMUL_BUTTER = uuid5(SEED_NAMESPACE, "amul-butter-100g")
PROD_DETTOL = uuid5(SEED_NAMESPACE, "dettol-soap-75g")


async def seed(session: AsyncSession) -> None:
    mock_adapter = MockSupplierAdapter()
    today = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)

    # 1. Merchants & Users
    merchants_and_users = [
        # Sharma General Store (Kirana Merchant)
        Merchant(
            id=SHARMA_MERCHANT_ID,
            name="Sharma General Store",
            phone_number="919999999999",
            currency="INR",
            spending_limit=Decimal("50000"),
            gstin="29ABCDE1234F1Z5",
            pan="ABCDE1234F",
            business_type="retail",
            settings={"demo": True},
        ),
        User(
            id=SHARMA_USER_ID,
            merchant_id=SHARMA_MERCHANT_ID,
            email="merchant@vyapaar.local",
            password_hash=hash_password("Vyapaar@123"),
            role="merchant",
            is_email_verified=True,
            is_phone_verified=True,
        ),
        Store(
            id=SHARMA_STORE_ID,
            merchant_id=SHARMA_MERCHANT_ID,
            name="Sharma Kirana Indiranagar",
            timezone="Asia/Kolkata",
            address={
                "flat": "Shop 14, Ground Floor",
                "street": "12th Main Road, HAL 2nd Stage",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560038",
                "locality": "Indiranagar, Bengaluru",
            },
        ),
        # Gupta Provision Store (Delhi Merchant)
        Merchant(
            id=GUPTA_MERCHANT_ID,
            name="Gupta Provision Store",
            phone_number="919888888888",
            currency="INR",
            spending_limit=Decimal("75000"),
            gstin="07ABCDE1234F1Z1",
            pan="ABCDE1234G",
            business_type="retail",
            settings={"demo": True},
        ),
        User(
            id=GUPTA_USER_ID,
            merchant_id=GUPTA_MERCHANT_ID,
            email="gupta@vyapaar.local",
            password_hash=hash_password("Vyapaar@123"),
            role="merchant",
            is_email_verified=True,
            is_phone_verified=True,
        ),
        Store(
            id=GUPTA_STORE_ID,
            merchant_id=GUPTA_MERCHANT_ID,
            name="Gupta Provision Karol Bagh",
            timezone="Asia/Kolkata",
            address={
                "flat": "Plot 8",
                "street": "Ajmal Khan Road",
                "city": "Delhi",
                "state": "Delhi",
                "postal_code": "110005",
                "locality": "Karol Bagh, New Delhi",
            },
        ),
        # Supplier Account (Bengaluru FMCG Hub)
        Merchant(
            id=SUPPLIER_MERCHANT_ID,
            name="Bengaluru FMCG Hub",
            phone_number="919777777777",
            currency="INR",
            spending_limit=Decimal("500000"),
            gstin="29XYZAB5678C1Z2",
            pan="XYZAB5678C",
            business_type="supplier",
            settings={"demo": True, "role": "supplier"},
        ),
        User(
            id=SUPPLIER_USER_ID,
            merchant_id=SUPPLIER_MERCHANT_ID,
            email="supplier@vyapaar.local",
            password_hash=hash_password("Vyapaar@123"),
            role="supplier",
            is_email_verified=True,
            is_phone_verified=True,
        ),
        Store(
            id=uuid5(SEED_NAMESPACE, "supplier-store-hub"),
            merchant_id=SUPPLIER_MERCHANT_ID,
            name="FMCG Wholesale Central Warehouse",
            timezone="Asia/Kolkata",
            address={
                "flat": "Warehouse 4B",
                "street": "Old Madras Road, Indiranagar",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560038",
            },
        ),
    ]
    for row in merchants_and_users:
        await session.merge(row)

    # 2. Suppliers
    suppliers = [
        # Connected B2B Supplier (Login account supplier@vyapaar.local)
        Supplier(
            id=BENGALURU_HUB_SUPPLIER_ID,
            merchant_id=SUPPLIER_MERCHANT_ID,
            name="Bengaluru FMCG Hub",
            adapter_type="rest",
            phone_number="919777777777",
            gstin="29XYZAB5678C1Z2",
            pan="XYZAB5678C",
            city="Bengaluru",
            state="Karnataka",
            pincode="560038",
            category="FMCG & Groceries",
            trust_score=Decimal("0.9800"),
            is_active=True,
            address={
                "flat": "Warehouse 4B",
                "street": "Old Madras Road, Indiranagar",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560038",
            },
            configuration={"deterministic": True, "role": "supplier"},
        ),
        # Bharat Beverage Wholesale (A2A Mock Adapter)
        Supplier(
            id=mock_adapter.supplier_id,
            merchant_id=SHARMA_MERCHANT_ID,
            name=mock_adapter.name,
            adapter_type="mock-a2a",
            phone_number="919900011122",
            gstin="29AABCB1234F1Z8",
            city="Bengaluru",
            state="Karnataka",
            pincode="560038",
            category="Beverages & Cold Drinks",
            trust_score=Decimal("0.9800"),
            is_active=True,
            address={"city": "Bengaluru", "state": "Karnataka", "pincode": "560038"},
            configuration={"deterministic": True},
        ),
        # Metro Wholesale Distributorship
        Supplier(
            id=METRO_SUPPLIER_ID,
            merchant_id=None,
            name="Metro Wholesale Distributorship",
            adapter_type="rest",
            phone_number="919666666666",
            gstin="29METRO1234A1Z9",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            category="Beverages & Staples",
            trust_score=Decimal("0.9500"),
            is_active=True,
            address={
                "flat": "Wholesale Block C",
                "street": "Yeshwanthpur APMC Yard",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001",
            },
            configuration={},
        ),
        # Delhi North FMCG Distributors
        Supplier(
            id=DELHI_SUPPLIER_ID,
            merchant_id=None,
            name="Delhi North FMCG Distributors",
            adapter_type="rest",
            phone_number="919555555555",
            gstin="07DELHI5678B1Z0",
            city="Delhi",
            state="Delhi",
            pincode="110007",
            category="FMCG & Groceries",
            trust_score=Decimal("0.9600"),
            is_active=True,
            address={
                "flat": "Shed 12",
                "street": "Azadpur Mandi",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110007",
            },
            configuration={},
        ),
    ]
    for s in suppliers:
        await session.merge(s)

    # 3. Products & Inventory (Sharma General Store)
    products = [
        Product(
            id=PROD_TATA_SALT,
            merchant_id=SHARMA_MERCHANT_ID,
            sku="TATA-SALT-1KG",
            name="Tata Salt 1kg",
            unit="pack",
            category="Staples",
            attributes={"brand": "Tata Consumer", "weight": "1kg"},
        ),
        Product(
            id=PROD_COLA,
            merchant_id=SHARMA_MERCHANT_ID,
            sku="COLD-COLA-300",
            name="Cola 300 ml crate",
            unit="crate",
            category="Cold Drinks",
            attributes={"units_per_crate": 24},
        ),
        Product(
            id=PROD_FORTUNE_OIL,
            merchant_id=SHARMA_MERCHANT_ID,
            sku="FORTUNE-OIL-1L",
            name="Fortune Sunlite Sunflower Oil 1L",
            unit="pouch",
            category="Cooking Essentials",
            attributes={"brand": "Fortune", "volume": "1L"},
        ),
        Product(
            id=PROD_ATTA,
            merchant_id=SHARMA_MERCHANT_ID,
            sku="AASHIRVAAD-ATTA-5KG",
            name="Aashirvaad Shudh Chakki Atta 5kg",
            unit="bag",
            category="Atta & Flours",
            attributes={"brand": "Aashirvaad", "weight": "5kg"},
        ),
        Product(
            id=PROD_MAGGI,
            merchant_id=SHARMA_MERCHANT_ID,
            sku="MAGGI-70G",
            name="Maggi 2-Minute Masala Noodles 70g",
            unit="pack",
            category="Snacks & Instant Food",
            attributes={"brand": "Nestle", "weight": "70g"},
        ),
        Product(
            id=PROD_PARLE_G,
            merchant_id=SHARMA_MERCHANT_ID,
            sku="PARLE-G-100G",
            name="Parle-G Gold Biscuits 100g",
            unit="pack",
            category="Bakery & Biscuits",
            attributes={"brand": "Parle", "weight": "100g"},
        ),
        Product(
            id=PROD_AMUL_BUTTER,
            merchant_id=SHARMA_MERCHANT_ID,
            sku="AMUL-BUTTER-100G",
            name="Amul Pasteurised Butter 100g",
            unit="pack",
            category="Dairy",
            attributes={"brand": "Amul", "weight": "100g"},
        ),
        Product(
            id=PROD_DETTOL,
            merchant_id=SHARMA_MERCHANT_ID,
            sku="DETTOL-SOAP-75G",
            name="Dettol Original Bathing Soap 75g",
            unit="bar",
            category="Personal Care",
            attributes={"brand": "Dettol", "pack_of": 4},
        ),
    ]
    for p in products:
        await session.merge(p)

    inventory_items = [
        # Low Stock Item 1: Tata Salt (4 on hand, reorder at 20) -> CRITICAL
        Inventory(
            id=uuid5(SEED_NAMESPACE, "inv-tata-salt"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            product_id=PROD_TATA_SALT,
            quantity_on_hand=Decimal("4"),
            reorder_point=Decimal("20"),
        ),
        # Low Stock Item 2: Cola Crate (3 on hand, reorder at 8) -> LOW STOCK
        Inventory(
            id=uuid5(SEED_NAMESPACE, "demo-inventory"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            product_id=PROD_COLA,
            quantity_on_hand=Decimal("3"),
            reorder_point=Decimal("8"),
        ),
        # Healthy items
        Inventory(
            id=uuid5(SEED_NAMESPACE, "inv-fortune-oil"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            product_id=PROD_FORTUNE_OIL,
            quantity_on_hand=Decimal("35"),
            reorder_point=Decimal("15"),
        ),
        Inventory(
            id=uuid5(SEED_NAMESPACE, "inv-atta"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            product_id=PROD_ATTA,
            quantity_on_hand=Decimal("22"),
            reorder_point=Decimal("10"),
        ),
        Inventory(
            id=uuid5(SEED_NAMESPACE, "inv-maggi"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            product_id=PROD_MAGGI,
            quantity_on_hand=Decimal("50"),
            reorder_point=Decimal("24"),
        ),
        Inventory(
            id=uuid5(SEED_NAMESPACE, "inv-parleg"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            product_id=PROD_PARLE_G,
            quantity_on_hand=Decimal("60"),
            reorder_point=Decimal("25"),
        ),
        Inventory(
            id=uuid5(SEED_NAMESPACE, "inv-amul-butter"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            product_id=PROD_AMUL_BUTTER,
            quantity_on_hand=Decimal("18"),
            reorder_point=Decimal("8"),
        ),
        Inventory(
            id=uuid5(SEED_NAMESPACE, "inv-dettol"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            product_id=PROD_DETTOL,
            quantity_on_hand=Decimal("30"),
            reorder_point=Decimal("12"),
        ),
    ]
    for inv in inventory_items:
        await session.merge(inv)

    # 4. Supplier Catalogs (Bengaluru FMCG Hub & Mock Supplier)
    supplier_products = [
        SupplierProduct(
            id=uuid5(SEED_NAMESPACE, "supplier-tata-salt"),
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            product_id=PROD_TATA_SALT,
            supplier_sku="HUB-TATA-SALT-1K",
            available_quantity=Decimal("500"),
            unit_price=Decimal("24.00"),
            lead_time_days=1,
        ),
        SupplierProduct(
            id=uuid5(SEED_NAMESPACE, "supplier-cold-cola"),
            supplier_id=mock_adapter.supplier_id,
            product_id=PROD_COLA,
            supplier_sku="BWW-COLA-300-24",
            available_quantity=Decimal("240"),
            unit_price=Decimal("470.00"),
            lead_time_days=1,
        ),
        SupplierProduct(
            id=uuid5(SEED_NAMESPACE, "supplier-hub-cola"),
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            product_id=PROD_COLA,
            supplier_sku="HUB-COLA-300-24",
            available_quantity=Decimal("300"),
            unit_price=Decimal("465.00"),
            lead_time_days=1,
        ),
        SupplierProduct(
            id=uuid5(SEED_NAMESPACE, "supplier-fortune-oil"),
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            product_id=PROD_FORTUNE_OIL,
            supplier_sku="HUB-FORTUNE-OIL-1L",
            available_quantity=Decimal("180"),
            unit_price=Decimal("138.00"),
            lead_time_days=1,
        ),
        SupplierProduct(
            id=uuid5(SEED_NAMESPACE, "supplier-atta"),
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            product_id=PROD_ATTA,
            supplier_sku="HUB-ATTA-5KG",
            available_quantity=Decimal("120"),
            unit_price=Decimal("215.00"),
            lead_time_days=1,
        ),
        SupplierProduct(
            id=uuid5(SEED_NAMESPACE, "supplier-maggi"),
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            product_id=PROD_MAGGI,
            supplier_sku="HUB-MAGGI-70G",
            available_quantity=Decimal("600"),
            unit_price=Decimal("11.50"),
            lead_time_days=1,
        ),
    ]
    for sp in supplier_products:
        await session.merge(sp)

    # 5. A2A Agents
    agents = [
        A2AAgent(
            id=BUYER_AGENT_ID,
            name="vyapaar-buyer-agent",
            endpoint="http://localhost:8000/api/v1/a2a/messages",
            shared_secret_ref="env:A2A_SIGNING_SECRET",
            allowed_intents=["PURCHASE_REQUEST", "COUNTER_OFFER", "OFFER_ACCEPTED"],
        ),
        A2AAgent(
            id=mock_adapter.supplier_id,
            name="bharat-beverage-mock-agent",
            endpoint="http://localhost:8000/api/v1/a2a/mock-supplier/messages",
            shared_secret_ref="env:A2A_SIGNING_SECRET",
            supplier_id=mock_adapter.supplier_id,
            allowed_intents=["QUOTE", "OFFER_REJECTED", "ORDER_CONFIRMATION"],
        ),
    ]
    for ag in agents:
        await session.merge(ag)

    # 6. Realistic Customers (Sharma General Store)
    customers = [
        Customer(
            id=uuid5(SEED_NAMESPACE, "cust-rajesh"),
            merchant_id=SHARMA_MERCHANT_ID,
            name="Rajesh Kumar",
            phone_number="+919811122233",
            email="rajesh.k@gmail.com",
            address={"locality": "Indiranagar 1st Stage", "city": "Bengaluru"},
            total_orders=14,
            total_spent=Decimal("8450.00"),
            last_visit=today - timedelta(hours=3),
        ),
        Customer(
            id=uuid5(SEED_NAMESPACE, "cust-priya"),
            merchant_id=SHARMA_MERCHANT_ID,
            name="Priya Sharma",
            phone_number="+919822233344",
            email="priya.sharma@yahoo.com",
            address={"locality": "HAL 2nd Stage", "city": "Bengaluru"},
            total_orders=8,
            total_spent=Decimal("4200.00"),
            last_visit=today - timedelta(hours=6),
        ),
        Customer(
            id=uuid5(SEED_NAMESPACE, "cust-ankit"),
            merchant_id=SHARMA_MERCHANT_ID,
            name="Ankit Verma",
            phone_number="+919833344455",
            email="ankit.v@hotmail.com",
            address={"locality": "Domlur Layout", "city": "Bengaluru"},
            total_orders=21,
            total_spent=Decimal("15300.00"),
            last_visit=today - timedelta(days=1, hours=2),
        ),
        Customer(
            id=uuid5(SEED_NAMESPACE, "cust-sunita"),
            merchant_id=SHARMA_MERCHANT_ID,
            name="Sunita Devi",
            phone_number="+919844455566",
            email=None,
            address={"locality": "Indiranagar 100ft Road", "city": "Bengaluru"},
            total_orders=5,
            total_spent=Decimal("2850.00"),
            last_visit=today - timedelta(days=2),
        ),
        Customer(
            id=uuid5(SEED_NAMESPACE, "cust-vikram"),
            merchant_id=SHARMA_MERCHANT_ID,
            name="Vikram Singh",
            phone_number="+919855566677",
            email="vikram.s@outlook.com",
            address={"locality": "Tippasandra", "city": "Bengaluru"},
            total_orders=11,
            total_spent=Decimal("6790.00"),
            last_visit=today - timedelta(days=3),
        ),
    ]
    for c in customers:
        await session.merge(c)

    # 7. Real Settlements (Today & Yesterday)
    settlements = [
        # Today's Expected Settlement
        Settlement(
            id=uuid5(SEED_NAMESPACE, "settlement-today"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            amount=Decimal("14250.00"),
            currency="INR",
            status="PROCESSING",
            bank_name="HDFC Bank",
            account_ending="4921",
            settlement_time="by 4:00 PM",
            settled_at=None,
        ),
        # Yesterday's Settled Payout
        Settlement(
            id=uuid5(SEED_NAMESPACE, "settlement-yesterday"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            amount=Decimal("28400.00"),
            currency="INR",
            status="SETTLED",
            utr="HDFCN2602189812",
            bank_name="HDFC Bank",
            account_ending="4921",
            settlement_time="Settled yesterday",
            settled_at=today - timedelta(days=1, hours=4),
        ),
    ]
    for st in settlements:
        await session.merge(st)

    # 8. Pending Replenishment Proposal & Approval (Tata Salt 1kg)
    proposal_id = uuid5(SEED_NAMESPACE, "proposal-tata-salt")
    approval_id = uuid5(SEED_NAMESPACE, "approval-tata-salt")
    proposal_payload = {
        "proposal_id": str(proposal_id),
        "merchant_id": str(SHARMA_MERCHANT_ID),
        "store_id": str(SHARMA_STORE_ID),
        "supplier_id": str(BENGALURU_HUB_SUPPLIER_ID),
        "sku": "TATA-SALT-1KG",
        "quantity": "20",
        "unit": "pack",
        "unit_price": "24.00",
        "currency": "INR",
        "delivery_at": (today + timedelta(days=1)).isoformat(),
        "quote_id": "QUOTE-HUB-TATA-2026",
    }
    order_hash = canonical_order_hash(proposal_payload)

    pending_approval = Approval(
        id=approval_id,
        merchant_id=SHARMA_MERCHANT_ID,
        proposal_id=proposal_id,
        order_hash=order_hash,
        proposal_payload=proposal_payload,
        status=ApprovalStatus.PENDING,
        nonce="nonce_demo_tata_salt_12345",
        expires_at=today + timedelta(days=7),
        channel="MunimAutonomousReplenishment",
        revision=1,
    )
    await session.merge(pending_approval)

    approval_notif = Notification(
        id=uuid5(SEED_NAMESPACE, "notif-tata-salt"),
        merchant_id=SHARMA_MERCHANT_ID,
        notification_type="APPROVAL_REQUIRED",
        title="⚠️ Low Stock Alert: Tata Salt 1kg",
        body="Stock down to 4 packs (reorder point: 20). Replenishment proposal ready for approval (20 packs @ ₹24.00 from Bengaluru FMCG Hub).",
        entity_type="approval",
        entity_id=approval_id,
        payload={"proposal_id": str(proposal_id)},
    )
    await session.merge(approval_notif)

    # 9. Incoming Wholesale Order for Supplier (Bengaluru FMCG Hub)
    supplier_incoming_order_id = uuid5(SEED_NAMESPACE, "supplier-incoming-order-1")
    supplier_order = Order(
        id=supplier_incoming_order_id,
        merchant_id=SHARMA_MERCHANT_ID,
        store_id=SHARMA_STORE_ID,
        supplier_id=BENGALURU_HUB_SUPPLIER_ID,
        proposal_id=uuid5(SEED_NAMESPACE, "supplier-prop-1"),
        order_hash=canonical_order_hash({"order": "demo-wholesale-1"}),
        status="CONFIRMED",
        currency="INR",
        total_amount=Decimal("2350.00"),
        idempotency_key="idemp-demo-supplier-order-1",
        supplier_reference="PO-2026-BLR-0042",
    )
    await session.merge(supplier_order)

    order_lines = [
        OrderItem(
            id=uuid5(SEED_NAMESPACE, "order-line-1"),
            order_id=supplier_incoming_order_id,
            product_id=PROD_MAGGI,
            sku="MAGGI-70G",
            quantity=Decimal("50"),
            unit="pack",
            unit_price=Decimal("11.50"),
        ),
        OrderItem(
            id=uuid5(SEED_NAMESPACE, "order-line-2"),
            order_id=supplier_incoming_order_id,
            product_id=PROD_ATTA,
            sku="AASHIRVAAD-ATTA-5KG",
            quantity=Decimal("8"),
            unit="bag",
            unit_price=Decimal("215.00"),
        ),
    ]
    for line in order_lines:
        await session.merge(line)

    # 10. Realistic 90-Day Sales History (Cola and Staples)
    for days_ago in range(90, 0, -1):
        sold_at = today - timedelta(days=days_ago)
        weekend = sold_at.weekday() >= 5
        festival = days_ago in {7, 35, 70}
        hot = days_ago < 21

        # Cola sales
        quantity_cola = 3 + int(weekend) * 2 + int(festival) * 3 + int(hot) * 2
        await session.merge(
            Sale(
                id=uuid5(SEED_NAMESPACE, f"sale-cola:{sold_at.date()}"),
                merchant_id=SHARMA_MERCHANT_ID,
                store_id=SHARMA_STORE_ID,
                product_id=PROD_COLA,
                quantity=Decimal(quantity_cola),
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

        # Tata Salt sales
        quantity_salt = 4 + int(weekend) * 2 + int(festival) * 4
        await session.merge(
            Sale(
                id=uuid5(SEED_NAMESPACE, f"sale-salt:{sold_at.date()}"),
                merchant_id=SHARMA_MERCHANT_ID,
                store_id=SHARMA_STORE_ID,
                product_id=PROD_TATA_SALT,
                quantity=Decimal(quantity_salt),
                unit_price=Decimal("28.00"),
                sold_at=sold_at,
                signals={
                    "festival_flag": festival,
                    "temperature_c": 28,
                    "promotion_flag": False,
                },
            )
        )

    # 11. Realistic A2A Agent Negotiations & Cryptographic Envelopes
    corr_cola = uuid5(SEED_NAMESPACE, "corr-cola-1")
    corr_salt = uuid5(SEED_NAMESPACE, "corr-tata-salt-1")

    negotiations = [
        # Negotiation 1: Cola 300 ml crate with Bharat Beverage Wholesale (A2A Mock)
        Negotiation(
            id=uuid5(SEED_NAMESPACE, "nego-cola-1"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            supplier_id=mock_adapter.supplier_id,
            correlation_id=corr_cola,
            workflow_request_id="auto_replenish_COLD-COLA-300_001",
            sku="COLD-COLA-300",
            status="ACCEPTED",
            round_count=3,
            constraints={
                "target_price": "435.00",
                "max_price": "480.00",
                "quantity": "10",
                "unit": "crate",
            },
            history=[
                {
                    "round": 1,
                    "action": "QUOTE_RECEIVED",
                    "status": "INITIAL_QUOTE",
                    "unit_price": "470.00",
                    "available_quantity": "240",
                    "delivery_at": (today + timedelta(days=1)).isoformat(),
                    "message": "Supplier quoted ₹470.00/crate",
                },
                {
                    "round": 2,
                    "action": "COUNTER_OFFER_SENT",
                    "status": "COUNTER_OFFER",
                    "unit_price": "435.00",
                    "quantity": "10",
                    "message": "Buyer agent countered at ₹435.00/crate",
                },
                {
                    "round": 2,
                    "action": "OFFER_ACCEPTED",
                    "status": "ACCEPTED",
                    "unit_price": "441.80",
                    "quantity": "10",
                    "message": "Negotiation concluded at ₹441.80/crate (Saved ₹28.20/crate = 6% savings)",
                },
            ],
            current_quote={
                "quote_id": "mock-cola-quote-001",
                "supplier_name": "Bharat Beverage Wholesale",
                "unit_price": "441.80",
                "quantity": "10",
                "currency": "INR",
            },
        ),
        # Negotiation 2: Tata Salt 1kg with Bengaluru FMCG Hub (Linked to pending approval)
        Negotiation(
            id=uuid5(SEED_NAMESPACE, "nego-tata-salt-1"),
            merchant_id=SHARMA_MERCHANT_ID,
            store_id=SHARMA_STORE_ID,
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            correlation_id=corr_salt,
            workflow_request_id="auto_replenish_TATA-SALT-1KG_002",
            proposal_id=proposal_id,
            sku="TATA-SALT-1KG",
            status="ACCEPTED",
            round_count=3,
            constraints={
                "target_price": "23.00",
                "max_price": "27.00",
                "quantity": "20",
                "unit": "pack",
            },
            history=[
                {
                    "round": 1,
                    "action": "QUOTE_RECEIVED",
                    "status": "INITIAL_QUOTE",
                    "unit_price": "26.00",
                    "available_quantity": "500",
                    "delivery_at": (today + timedelta(days=1)).isoformat(),
                    "message": "Bengaluru FMCG Hub initial quote: ₹26.00/pack",
                },
                {
                    "round": 2,
                    "action": "COUNTER_OFFER_SENT",
                    "status": "COUNTER_OFFER",
                    "unit_price": "23.00",
                    "quantity": "20",
                    "message": "Buyer agent countered at ₹23.00/pack",
                },
                {
                    "round": 2,
                    "action": "OFFER_ACCEPTED",
                    "status": "ACCEPTED",
                    "unit_price": "24.00",
                    "quantity": "20",
                    "message": "Agreed at ₹24.00/pack (Saved ₹2.00/pack = 7.7% savings)",
                },
            ],
            current_quote={
                "quote_id": "QUOTE-HUB-TATA-2026",
                "supplier_name": "Bengaluru FMCG Hub",
                "unit_price": "24.00",
                "quantity": "20",
                "currency": "INR",
            },
        ),
    ]
    for n in negotiations:
        await session.merge(n)

    a2a_messages = [
        # Cola A2A exchange
        A2AMessage(
            id=uuid5(SEED_NAMESPACE, "msg-cola-1"),
            merchant_id=SHARMA_MERCHANT_ID,
            supplier_id=mock_adapter.supplier_id,
            negotiation_id=uuid5(SEED_NAMESPACE, "nego-cola-1"),
            message_id=uuid5(SEED_NAMESPACE, "env-cola-1"),
            correlation_id=corr_cola,
            trace_id="trace-cola-nego-001",
            sender_agent_id=BUYER_AGENT_ID,
            receiver_agent_id=mock_adapter.supplier_id,
            intent="PURCHASE_REQUEST",
            direction="OUTBOUND",
            status="SENT",
            nonce="nonce-cola-rfq-001",
            idempotency_key="idemp-cola-rfq-001",
            envelope={
                "protocol_version": "vyapaar-a2a-v1",
                "intent": "PURCHASE_REQUEST",
                "sku": "COLD-COLA-300",
                "quantity": "10",
                "target_price": "435.00",
            },
            expires_at=today + timedelta(minutes=15),
            processed_at=today - timedelta(hours=2),
        ),
        A2AMessage(
            id=uuid5(SEED_NAMESPACE, "msg-cola-2"),
            merchant_id=SHARMA_MERCHANT_ID,
            supplier_id=mock_adapter.supplier_id,
            negotiation_id=uuid5(SEED_NAMESPACE, "nego-cola-1"),
            message_id=uuid5(SEED_NAMESPACE, "env-cola-2"),
            correlation_id=corr_cola,
            trace_id="trace-cola-nego-001",
            sender_agent_id=mock_adapter.supplier_id,
            receiver_agent_id=BUYER_AGENT_ID,
            intent="QUOTE",
            direction="INBOUND",
            status="RECEIVED",
            nonce="nonce-cola-quote-001",
            idempotency_key="idemp-cola-quote-001",
            envelope={
                "protocol_version": "vyapaar-a2a-v1",
                "intent": "QUOTE",
                "sku": "COLD-COLA-300",
                "unit_price": "470.00",
                "available_quantity": "240",
            },
            expires_at=today + timedelta(minutes=15),
            processed_at=today - timedelta(hours=2, minutes=-1),
        ),
        A2AMessage(
            id=uuid5(SEED_NAMESPACE, "msg-cola-3"),
            merchant_id=SHARMA_MERCHANT_ID,
            supplier_id=mock_adapter.supplier_id,
            negotiation_id=uuid5(SEED_NAMESPACE, "nego-cola-1"),
            message_id=uuid5(SEED_NAMESPACE, "env-cola-3"),
            correlation_id=corr_cola,
            trace_id="trace-cola-nego-001",
            sender_agent_id=BUYER_AGENT_ID,
            receiver_agent_id=mock_adapter.supplier_id,
            intent="COUNTER_OFFER",
            direction="OUTBOUND",
            status="SENT",
            nonce="nonce-cola-counter-001",
            idempotency_key="idemp-cola-counter-001",
            envelope={
                "protocol_version": "vyapaar-a2a-v1",
                "intent": "COUNTER_OFFER",
                "quote_id": "mock-cola-quote-001",
                "unit_price": "435.00",
                "quantity": "10",
            },
            expires_at=today + timedelta(minutes=15),
            processed_at=today - timedelta(hours=2, minutes=-2),
        ),
        A2AMessage(
            id=uuid5(SEED_NAMESPACE, "msg-cola-4"),
            merchant_id=SHARMA_MERCHANT_ID,
            supplier_id=mock_adapter.supplier_id,
            negotiation_id=uuid5(SEED_NAMESPACE, "nego-cola-1"),
            message_id=uuid5(SEED_NAMESPACE, "env-cola-4"),
            correlation_id=corr_cola,
            trace_id="trace-cola-nego-001",
            sender_agent_id=mock_adapter.supplier_id,
            receiver_agent_id=BUYER_AGENT_ID,
            intent="QUOTE",
            direction="INBOUND",
            status="RECEIVED",
            nonce="nonce-cola-revised-001",
            idempotency_key="idemp-cola-revised-001",
            envelope={
                "protocol_version": "vyapaar-a2a-v1",
                "intent": "QUOTE",
                "quote_id": "mock-cola-quote-001",
                "unit_price": "441.80",
                "available_quantity": "240",
            },
            expires_at=today + timedelta(minutes=15),
            processed_at=today - timedelta(hours=2, minutes=-3),
        ),
        # Tata Salt A2A exchange
        A2AMessage(
            id=uuid5(SEED_NAMESPACE, "msg-salt-1"),
            merchant_id=SHARMA_MERCHANT_ID,
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            negotiation_id=uuid5(SEED_NAMESPACE, "nego-tata-salt-1"),
            message_id=uuid5(SEED_NAMESPACE, "env-salt-1"),
            correlation_id=corr_salt,
            trace_id="trace-salt-nego-001",
            sender_agent_id=BUYER_AGENT_ID,
            receiver_agent_id=BENGALURU_HUB_SUPPLIER_ID,
            intent="PURCHASE_REQUEST",
            direction="OUTBOUND",
            status="SENT",
            nonce="nonce-salt-rfq-001",
            idempotency_key="idemp-salt-rfq-001",
            envelope={
                "protocol_version": "vyapaar-a2a-v1",
                "intent": "PURCHASE_REQUEST",
                "sku": "TATA-SALT-1KG",
                "quantity": "20",
                "target_price": "23.00",
            },
            expires_at=today + timedelta(minutes=15),
            processed_at=today - timedelta(hours=1),
        ),
        A2AMessage(
            id=uuid5(SEED_NAMESPACE, "msg-salt-2"),
            merchant_id=SHARMA_MERCHANT_ID,
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            negotiation_id=uuid5(SEED_NAMESPACE, "nego-tata-salt-1"),
            message_id=uuid5(SEED_NAMESPACE, "env-salt-2"),
            correlation_id=corr_salt,
            trace_id="trace-salt-nego-001",
            sender_agent_id=BENGALURU_HUB_SUPPLIER_ID,
            receiver_agent_id=BUYER_AGENT_ID,
            intent="QUOTE",
            direction="INBOUND",
            status="RECEIVED",
            nonce="nonce-salt-quote-001",
            idempotency_key="idemp-salt-quote-001",
            envelope={
                "protocol_version": "vyapaar-a2a-v1",
                "intent": "QUOTE",
                "sku": "TATA-SALT-1KG",
                "unit_price": "26.00",
                "available_quantity": "500",
            },
            expires_at=today + timedelta(minutes=15),
            processed_at=today - timedelta(hours=1, minutes=-1),
        ),
        A2AMessage(
            id=uuid5(SEED_NAMESPACE, "msg-salt-3"),
            merchant_id=SHARMA_MERCHANT_ID,
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            negotiation_id=uuid5(SEED_NAMESPACE, "nego-tata-salt-1"),
            message_id=uuid5(SEED_NAMESPACE, "env-salt-3"),
            correlation_id=corr_salt,
            trace_id="trace-salt-nego-001",
            sender_agent_id=BUYER_AGENT_ID,
            receiver_agent_id=BENGALURU_HUB_SUPPLIER_ID,
            intent="COUNTER_OFFER",
            direction="OUTBOUND",
            status="SENT",
            nonce="nonce-salt-counter-001",
            idempotency_key="idemp-salt-counter-001",
            envelope={
                "protocol_version": "vyapaar-a2a-v1",
                "intent": "COUNTER_OFFER",
                "quote_id": "QUOTE-HUB-TATA-2026",
                "unit_price": "23.00",
                "quantity": "20",
            },
            expires_at=today + timedelta(minutes=15),
            processed_at=today - timedelta(hours=1, minutes=-2),
        ),
        A2AMessage(
            id=uuid5(SEED_NAMESPACE, "msg-salt-4"),
            merchant_id=SHARMA_MERCHANT_ID,
            supplier_id=BENGALURU_HUB_SUPPLIER_ID,
            negotiation_id=uuid5(SEED_NAMESPACE, "nego-tata-salt-1"),
            message_id=uuid5(SEED_NAMESPACE, "env-salt-4"),
            correlation_id=corr_salt,
            trace_id="trace-salt-nego-001",
            sender_agent_id=BENGALURU_HUB_SUPPLIER_ID,
            receiver_agent_id=BUYER_AGENT_ID,
            intent="QUOTE",
            direction="INBOUND",
            status="RECEIVED",
            nonce="nonce-salt-revised-001",
            idempotency_key="idemp-salt-revised-001",
            envelope={
                "protocol_version": "vyapaar-a2a-v1",
                "intent": "QUOTE",
                "quote_id": "QUOTE-HUB-TATA-2026",
                "unit_price": "24.00",
                "available_quantity": "500",
            },
            expires_at=today + timedelta(minutes=15),
            processed_at=today - timedelta(hours=1, minutes=-3),
        ),
    ]
    for msg in a2a_messages:
        await session.merge(msg)


async def main() -> None:
    async with get_session_factory()() as session, session.begin():
        await seed(session)
    print("Successfully seeded realistic Kirana operations data:")
    print("  ✓ Merchant: merchant@vyapaar.local / Vyapaar@123 (Sharma General Store, Bengaluru)")
    print("  ✓ Merchant: gupta@vyapaar.local / Vyapaar@123 (Gupta Provision Store, Delhi)")
    print("  ✓ Supplier: supplier@vyapaar.local / Vyapaar@123 (Bengaluru FMCG Hub)")
    print("  ✓ 8 Kirana Products (Tata Salt, Cola crate, Fortune Oil, Atta, Maggi, Parle-G, Amul, Dettol)")
    print("  ✓ Low Stock Trigger: Tata Salt 1kg (4 on hand, reorder 20)")
    print("  ✓ Low Stock Trigger: Cola 300ml Crate (3 on hand, reorder 8)")
    print("  ✓ Pending Replenishment Approval for Tata Salt ready for review")
    print("  ✓ Incoming Wholesale Order for Bengaluru FMCG Hub")
    print("  ✓ 5 Real Customers with order counts & spending")
    print("  ✓ Expected Today + Settled Yesterday HDFC Bank Settlements")
    print("  ✓ 90 Days of Realistic Sales Data")


if __name__ == "__main__":
    asyncio.run(main())
