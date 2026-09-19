from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ApprovalStatus
from app.infrastructure.db.models import (
    Approval,
    Inventory,
    InventoryEvent,
    Merchant,
    Order,
    Product,
    Sale,
    Settlement,
    Store,
    Supplier,
    SupplierProduct,
    Transaction,
)


class MunimToolRegistry:
    """Executes grounded tools for the Munim Assistant in an authenticated session."""

    def __init__(self, session: AsyncSession, merchant_id: UUID, role: str = "merchant") -> None:
        self.session = session
        self.merchant_id = merchant_id
        self.role = role

    async def get_business_profile(self) -> dict[str, Any]:
        merchant = await self.session.get(Merchant, self.merchant_id)
        store = await self.session.scalar(
            select(Store).where(Store.merchant_id == self.merchant_id).limit(1)
        )
        return {
            "business_name": merchant.name if merchant else "My Business",
            "role": self.role,
            "legal_name": getattr(merchant, "legal_name", None)
            or (merchant.name if merchant else ""),
            "gstin": getattr(merchant, "gstin", None),
            "pan": getattr(merchant, "pan", None),
            "business_type": getattr(merchant, "business_type", "retail"),
            "city": store.city if store else None,
            "state": store.state if store else None,
            "pincode": store.pincode if store else None,
            "address": store.address_line1 if store else None,
            "currency": merchant.currency if merchant else "INR",
        }

    async def get_inventory_summary(self) -> dict[str, Any]:
        total_prods = (
            await self.session.scalar(
                select(func.count(Product.id)).where(Product.merchant_id == self.merchant_id)
            )
        ) or 0
        available_rows = (
            await self.session.execute(
                select(
                    Product.name,
                    Product.sku,
                    Product.unit,
                    Inventory.quantity_on_hand,
                    Inventory.reorder_point,
                )
                .join(Product, Inventory.product_id == Product.id)
                .where(Inventory.merchant_id == self.merchant_id)
                .order_by(Inventory.quantity_on_hand.desc())
                .limit(20)
            )
        ).all()
        available_items = [
            {
                "name": r[0],
                "sku": r[1],
                "unit": r[2],
                "quantity_on_hand": float(r[3]),
                "reorder_point": float(r[4]),
            }
            for r in available_rows
        ]
        low_stock_rows = (
            await self.session.execute(
                select(
                    Product.name,
                    Product.sku,
                    Product.unit,
                    Inventory.quantity_on_hand,
                    Inventory.reorder_point,
                )
                .join(Product, Inventory.product_id == Product.id)
                .where(
                    Inventory.merchant_id == self.merchant_id,
                    Inventory.quantity_on_hand <= Inventory.reorder_point,
                )
                .order_by(Inventory.quantity_on_hand.asc())
                .limit(10)
            )
        ).all()
        low_stock_items = [
            {
                "name": r[0],
                "sku": r[1],
                "unit": r[2],
                "quantity_on_hand": float(r[3]),
                "reorder_point": float(r[4]),
            }
            for r in low_stock_rows
        ]
        event_rows = (
            await self.session.execute(
                select(
                    Product.name,
                    Product.sku,
                    InventoryEvent.event_type,
                    InventoryEvent.quantity_delta,
                    InventoryEvent.quantity_after,
                    InventoryEvent.source,
                    InventoryEvent.created_at,
                )
                .join(Product, Product.id == InventoryEvent.product_id)
                .where(InventoryEvent.merchant_id == self.merchant_id)
                .order_by(InventoryEvent.created_at.desc())
                .limit(10)
            )
        ).all()
        return {
            "total_products": total_prods,
            "available_items": available_items,
            "items": available_items,
            "low_stock_count": len(low_stock_items),
            "low_stock_items": low_stock_items,
            "recent_inventory_events": [
                {
                    "name": row[0],
                    "sku": row[1],
                    "event_type": row[2],
                    "quantity_delta": float(row[3]),
                    "quantity_after": float(row[4]),
                    "source": row[5],
                    "created_at": row[6].isoformat(),
                }
                for row in event_rows
            ],
        }

    async def get_transaction_summary(self) -> dict[str, Any]:
        rows = list(
            await self.session.scalars(
                select(Transaction)
                .where(Transaction.merchant_id == self.merchant_id)
                .order_by(Transaction.created_at.desc())
                .limit(20)
            )
        )
        transaction_count = (
            await self.session.scalar(
                select(func.count(Transaction.id)).where(
                    Transaction.merchant_id == self.merchant_id
                )
            )
        ) or 0
        successful_amount = Decimal(
            str(
                await self.session.scalar(
                    select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                        Transaction.merchant_id == self.merchant_id,
                        Transaction.status == "SUCCEEDED",
                    )
                )
                or 0
            )
        )
        pending_amount = Decimal(
            str(
                await self.session.scalar(
                    select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                        Transaction.merchant_id == self.merchant_id,
                        Transaction.status == "PENDING",
                    )
                )
                or 0
            )
        )
        return {
            "transaction_count": transaction_count,
            "successful_amount": float(successful_amount),
            "pending_amount": float(pending_amount),
            "recent_transactions": [
                {
                    "transaction_id": str(row.id),
                    "order_id": str(row.order_id),
                    "amount": float(row.amount),
                    "status": row.status,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ],
        }

    async def get_sales_report(self) -> dict[str, Any]:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        row = (
            await self.session.execute(
                select(
                    func.coalesce(func.sum(Sale.quantity * Sale.unit_price), 0),
                    func.count(Sale.id),
                ).where(Sale.merchant_id == self.merchant_id, Sale.sold_at >= today_start)
            )
        ).first()
        return {
            "today_sales_amount": float(row[0]) if row else 0.0,
            "today_transactions": row[1] if row else 0,
            "currency": "INR",
        }

    async def get_settlements(self) -> dict[str, Any]:
        rows = list(
            await self.session.scalars(
                select(Settlement)
                .where(Settlement.merchant_id == self.merchant_id)
                .order_by(Settlement.created_at.desc())
            )
        )
        proc = next((r for r in rows if r.status == "PROCESSING"), None)
        settled = next((r for r in rows if r.status == "SETTLED"), None)
        return {
            "expected_today": float(proc.amount) if proc else 0.0,
            "yesterday_settled": float(settled.amount) if settled else 0.0,
            "status": proc.status if proc else "Settled",
            "bank_name": (proc or settled).bank_name if (proc or settled) else "HDFC Bank",
            "account_ending": (proc or settled).account_ending if (proc or settled) else "4921",
            "utr": (settled or proc).utr if (settled or proc) else "PAYTMUTR000000",
        }

    async def search_suppliers(
        self, search: str | None = None, city: str | None = None
    ) -> list[dict]:
        query = select(Supplier).where(Supplier.is_active.is_(True))
        if search:
            query = query.where(
                or_(Supplier.name.ilike(f"%{search}%"), Supplier.category.ilike(f"%{search}%"))
            )
        if city:
            query = query.where(Supplier.city.ilike(f"%{city}%"))
        suppliers = list(await self.session.scalars(query.limit(10)))
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "city": s.city,
                "category": s.category,
                "trust_score": float(s.trust_score) if s.trust_score else 0.95,
                "phone_number": s.phone_number,
            }
            for s in suppliers
        ]

    async def compare_supplier_prices(self, sku: str) -> list[dict]:
        product = await self.session.scalar(
            select(Product).where(Product.merchant_id == self.merchant_id, Product.sku == sku)
        )
        if not product:
            return []
        rows = (
            await self.session.execute(
                select(SupplierProduct, Supplier)
                .join(Supplier, Supplier.id == SupplierProduct.supplier_id)
                .where(SupplierProduct.product_id == product.id, Supplier.is_active.is_(True))
                .order_by(SupplierProduct.unit_price.asc())
            )
        ).tuples()
        return [
            {
                "supplier_name": supplier.name,
                "supplier_id": str(supplier.id),
                "unit_price": float(sp.unit_price),
                "available_quantity": float(sp.available_quantity),
                "lead_time_days": sp.lead_time_days,
                "trust_score": float(supplier.trust_score) if supplier.trust_score else 0.95,
            }
            for sp, supplier in rows
        ]

    async def get_pending_approvals(self) -> list[dict]:
        approvals = list(
            await self.session.scalars(
                select(Approval)
                .where(
                    Approval.merchant_id == self.merchant_id,
                    Approval.status == ApprovalStatus.PENDING,
                )
                .order_by(Approval.created_at.desc())
            )
        )
        items = []
        for a in approvals:
            p = a.proposal_payload or {}
            items.append(
                {
                    "approval_id": str(a.id),
                    "proposal_id": str(a.proposal_id),
                    "sku": p.get("sku"),
                    "quantity": float(p.get("quantity", 0)),
                    "unit": p.get("unit"),
                    "unit_price": float(p.get("unit_price", 0)),
                    "total_amount": float(
                        Decimal(str(p.get("quantity", 0))) * Decimal(str(p.get("unit_price", 0)))
                    ),
                    "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                }
            )
        return items

    # --- Supplier Specific Tools ---
    async def get_supplier_catalog(self) -> list[dict]:
        supplier = await self.session.scalar(
            select(Supplier).where(Supplier.merchant_id == self.merchant_id)
        )
        if not supplier:
            return []
        rows = (
            await self.session.execute(
                select(SupplierProduct, Product)
                .join(Product, Product.id == SupplierProduct.product_id)
                .where(SupplierProduct.supplier_id == supplier.id)
            )
        ).tuples()
        return [
            {
                "product_name": prod.name,
                "sku": prod.sku,
                "unit": prod.unit,
                "unit_price": float(sp.unit_price),
                "available_quantity": float(sp.available_quantity),
                "lead_time_days": sp.lead_time_days,
            }
            for sp, prod in rows
        ]

    async def get_incoming_orders(self) -> list[dict]:
        supplier = await self.session.scalar(
            select(Supplier).where(Supplier.merchant_id == self.merchant_id)
        )
        if not supplier:
            return []
        orders = list(
            await self.session.scalars(
                select(Order)
                .where(Order.supplier_id == supplier.id)
                .order_by(Order.created_at.desc())
                .limit(20)
            )
        )
        items = []
        for o in orders:
            m = await self.session.get(Merchant, o.merchant_id)
            items.append(
                {
                    "order_id": str(o.id),
                    "merchant_name": m.name if m else "Store",
                    "total_amount": float(o.total_amount),
                    "status": o.status,
                    "created_at": o.created_at.isoformat(),
                }
            )
        return items


TOOL_DEFINITIONS = [
    {
        "name": "get_business_profile",
        "description": "Get business registration, GSTIN, PAN, and store location details.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_inventory_summary",
        "description": "Get inventory counts, products, and list of items below reorder threshold.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_sales_report",
        "description": "Get today's total revenue, transaction counts, and sales status.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_transaction_summary",
        "description": "Get live procurement transaction totals, settlement state, and recent purchase transactions.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_settlements",
        "description": "Get settlement payouts, expected today amount, bank account details, and UTR.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "search_suppliers",
        "description": "Search active suppliers by category, name, or city.",
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Supplier name or product category"},
                "city": {"type": "string", "description": "Filter by city"},
            },
        },
    },
    {
        "name": "compare_supplier_prices",
        "description": "Compare wholesale unit prices and delivery lead times across suppliers for a given SKU.",
        "parameters": {
            "type": "object",
            "properties": {"sku": {"type": "string", "description": "Product SKU code"}},
            "required": ["sku"],
        },
    },
    {
        "name": "get_pending_approvals",
        "description": "Get pending autonomous procurement proposals awaiting merchant approval.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_supplier_catalog",
        "description": "For supplier accounts: get the list of wholesale products and current inventory.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_incoming_orders",
        "description": "For supplier accounts: list incoming purchase orders from retail kirana stores.",
        "parameters": {"type": "object", "properties": {}},
    },
]
