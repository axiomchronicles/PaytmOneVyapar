from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ApprovalStatus, OrderStatus
from app.infrastructure.db.models import (
    Approval,
    Customer,
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


class MunimContextService:
    """Provides scoped, real-time business facts for the Munim conversational and voice agents."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_business_context(
        self, merchant_id: UUID, *, role: str = "merchant"
    ) -> dict[str, Any]:
        """Gathers complete live business facts for the authenticated merchant or supplier."""
        if role == "supplier":
            return await self._get_supplier_context(merchant_id)
        return await self._get_merchant_context(merchant_id)

    async def _get_merchant_context(self, merchant_id: UUID) -> dict[str, Any]:
        merchant = await self.session.get(Merchant, merchant_id)
        merchant_name = merchant.name if merchant else "Merchant"
        currency = merchant.currency if merchant and merchant.currency else "INR"
        gstin = merchant.gstin if merchant else None
        pan = merchant.pan if merchant else None
        business_type = getattr(merchant, "business_type", "Kirana / Retail") or "Kirana / Retail"

        store = await self.session.scalar(
            select(Store).where(Store.merchant_id == merchant_id).limit(1)
        )
        store_address = "Address not registered"
        if store:
            parts = [p for p in [store.address_line1, store.city, store.state] if p]
            if parts and store.pincode:
                store_address = f"{', '.join(parts)} - {store.pincode}"
            elif parts:
                store_address = ", ".join(parts)
            elif store.pincode:
                store_address = f"PIN {store.pincode}"

        # Inventory facts
        prod_count = (
            await self.session.scalar(
                select(func.count(Product.id)).where(Product.merchant_id == merchant_id)
            )
        ) or 0

        # Available inventory items
        inv_stmt = (
            select(
                Product.name,
                Product.sku,
                Product.unit,
                Inventory.quantity_on_hand,
                Inventory.reorder_point,
            )
            .join(Product, Inventory.product_id == Product.id)
            .where(Inventory.merchant_id == merchant_id)
            .order_by(Inventory.quantity_on_hand.desc())
            .limit(20)
        )
        inv_items_rows = (await self.session.execute(inv_stmt)).all()
        inventory_items = [
            {
                "name": row[0],
                "sku": row[1],
                "unit": row[2],
                "quantity_on_hand": float(row[3]),
                "reorder_point": float(row[4]),
            }
            for row in inv_items_rows
        ]

        low_inv_stmt = (
            select(
                Product.name,
                Product.sku,
                Product.unit,
                Inventory.quantity_on_hand,
                Inventory.reorder_point,
            )
            .join(Product, Inventory.product_id == Product.id)
            .where(
                Inventory.merchant_id == merchant_id,
                Inventory.quantity_on_hand <= Inventory.reorder_point,
            )
            .order_by(Inventory.quantity_on_hand.asc())
            .limit(10)
        )
        low_items_rows = (await self.session.execute(low_inv_stmt)).all()
        low_stock_items = [
            {
                "name": row[0],
                "sku": row[1],
                "unit": row[2],
                "quantity_on_hand": float(row[3]),
                "reorder_point": float(row[4]),
                "safety_stock": 0.0,
                "deficit": float(row[4] - row[3]),
            }
            for row in low_items_rows
        ]

        recent_inventory_rows = (
            await self.session.execute(
                select(
                    Product.name,
                    Product.sku,
                    Product.unit,
                    InventoryEvent.event_type,
                    InventoryEvent.quantity_delta,
                    InventoryEvent.quantity_after,
                    InventoryEvent.source,
                    InventoryEvent.created_at,
                )
                .join(Product, Product.id == InventoryEvent.product_id)
                .where(InventoryEvent.merchant_id == merchant_id)
                .order_by(InventoryEvent.created_at.desc())
                .limit(10)
            )
        ).all()
        recent_inventory_events = [
            {
                "name": row[0],
                "sku": row[1],
                "unit": row[2],
                "event_type": row[3],
                "quantity_delta": float(row[4]),
                "quantity_after": float(row[5]),
                "source": row[6],
                "created_at": row[7].isoformat(),
            }
            for row in recent_inventory_rows
        ]

        # Value stock from the current active supplier catalog. Products do not
        # own a price; supplier quotes are the source of purchase pricing.
        stock_value = Decimal("0.00")
        stock_rows = (
            await self.session.execute(
                select(Inventory.quantity_on_hand, Inventory.product_id).where(
                    Inventory.merchant_id == merchant_id
                )
            )
        ).all()
        for quantity_on_hand, product_id in stock_rows:
            unit_price = await self.session.scalar(
                select(func.min(SupplierProduct.unit_price))
                .join(Supplier, Supplier.id == SupplierProduct.supplier_id)
                .where(
                    SupplierProduct.product_id == product_id,
                    Supplier.is_active.is_(True),
                )
            )
            if unit_price is None:
                unit_price = await self.session.scalar(
                    select(Sale.unit_price)
                    .where(Sale.merchant_id == merchant_id, Sale.product_id == product_id)
                    .order_by(Sale.sold_at.desc())
                    .limit(1)
                )
            if unit_price is not None:
                stock_value += quantity_on_hand * unit_price

        # Today's Sales
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        today_sales_stmt = select(
            func.coalesce(func.sum(Sale.quantity * Sale.unit_price), 0),
            func.count(Sale.id),
        ).where(Sale.merchant_id == merchant_id, Sale.sold_at >= today_start)
        sales_row = (await self.session.execute(today_sales_stmt)).first()
        today_sales_amount = sales_row[0] if sales_row else Decimal("0.00")
        today_sales_count = sales_row[1] if sales_row else 0

        transaction_rows = list(
            await self.session.scalars(
                select(Transaction)
                .where(Transaction.merchant_id == merchant_id)
                .order_by(Transaction.created_at.desc())
                .limit(10)
            )
        )
        transaction_count = (
            await self.session.scalar(
                select(func.count(Transaction.id)).where(Transaction.merchant_id == merchant_id)
            )
        ) or 0
        successful_transaction_amount = Decimal(
            str(
                await self.session.scalar(
                    select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                        Transaction.merchant_id == merchant_id,
                        Transaction.status == "SUCCEEDED",
                    )
                )
                or 0
            )
        )
        pending_transaction_amount = Decimal(
            str(
                await self.session.scalar(
                    select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                        Transaction.merchant_id == merchant_id,
                        Transaction.status == "PENDING",
                    )
                )
                or 0
            )
        )
        recent_transactions = [
            {
                "transaction_id": str(row.id),
                "order_id": str(row.order_id),
                "amount": float(row.amount),
                "currency": row.currency,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
            }
            for row in transaction_rows
        ]

        # Customers
        total_customers = (
            await self.session.scalar(
                select(func.count(Customer.id)).where(Customer.merchant_id == merchant_id)
            )
        ) or 0

        top_customers_rows = list(
            await self.session.scalars(
                select(Customer)
                .where(Customer.merchant_id == merchant_id)
                .order_by(Customer.total_spent.desc())
                .limit(3)
            )
        )
        top_customers = [
            {"name": c.name, "phone": c.phone_number, "total_spent": float(c.total_spent)}
            for c in top_customers_rows
        ]

        # Settlements
        settlement_stmt = (
            select(Settlement)
            .where(Settlement.merchant_id == merchant_id)
            .order_by(Settlement.created_at.desc())
        )
        settlement_rows = list(await self.session.scalars(settlement_stmt))
        processing = next((r for r in settlement_rows if r.status == "PROCESSING"), None)
        settled = next((r for r in settlement_rows if r.status == "SETTLED"), None)
        expected_settlement = float(processing.amount) if processing else 0.0
        yesterday_settled = float(settled.amount) if settled else 0.0
        bank_name = (processing or settled).bank_name if (processing or settled) else "HDFC Bank"
        account_ending = (
            (processing or settled).account_ending if (processing or settled) else "4921"
        )

        # Pending Approvals
        approvals_stmt = (
            select(Approval)
            .where(Approval.merchant_id == merchant_id, Approval.status == ApprovalStatus.PENDING)
            .order_by(Approval.created_at.desc())
            .limit(5)
        )
        approval_rows = list(await self.session.scalars(approvals_stmt))
        pending_approvals = []
        for a in approval_rows:
            p = a.proposal_payload or {}
            pending_approvals.append(
                {
                    "approval_id": str(a.id),
                    "proposal_id": str(a.proposal_id),
                    "sku": p.get("sku", "Unknown"),
                    "quantity": float(p.get("quantity", 0)),
                    "unit": p.get("unit", "units"),
                    "unit_price": float(p.get("unit_price", 0)),
                    "total_amount": float(
                        Decimal(str(p.get("quantity", 0))) * Decimal(str(p.get("unit_price", 0)))
                    ),
                    "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                }
            )

        # Active Suppliers
        suppliers_stmt = (
            select(Supplier)
            .where(
                Supplier.is_active.is_(True),
                (Supplier.merchant_id == merchant_id) | (Supplier.merchant_id.is_(None)),
            )
            .limit(5)
        )
        suppliers_rows = list(await self.session.scalars(suppliers_stmt))
        suppliers_list = [
            {
                "id": str(s.id),
                "name": s.name,
                "city": s.city or "Local",
                "category": s.category or "General FMCG",
                "trust_score": float(s.trust_score) if s.trust_score else 0.95,
            }
            for s in suppliers_rows
        ]

        return {
            "account_type": "merchant",
            "business_name": merchant_name,
            "currency": currency,
            "gstin": gstin,
            "pan": pan,
            "business_type": business_type,
            "store_address": store_address,
            "total_products": prod_count,
            "total_inventory_value": float(stock_value),
            "inventory_items": inventory_items,
            "available_items": inventory_items,
            "recent_inventory_events": recent_inventory_events,
            "low_stock_count": len(low_stock_items),
            "low_stock_items": low_stock_items,
            "today_sales_amount": float(today_sales_amount),
            "today_sales_count": today_sales_count,
            "transaction_count": transaction_count,
            "successful_transaction_amount": float(successful_transaction_amount),
            "pending_transaction_amount": float(pending_transaction_amount),
            "recent_transactions": recent_transactions,
            "total_customers": total_customers,
            "top_customers": top_customers,
            "expected_settlement": expected_settlement,
            "yesterday_settled": yesterday_settled,
            "bank_name": bank_name,
            "account_ending": account_ending,
            "pending_approvals": pending_approvals,
            "suppliers": suppliers_list,
        }

    async def _get_supplier_context(self, merchant_id: UUID) -> dict[str, Any]:
        supplier = await self.session.scalar(
            select(Supplier).where(Supplier.merchant_id == merchant_id)
        )
        if not supplier:
            merchant = await self.session.get(Merchant, merchant_id)
            name = merchant.name if merchant else "Supplier"
            supplier = await self.session.scalar(select(Supplier).where(Supplier.name == name))

        supplier_name = supplier.name if supplier else "Supplier Hub"
        city = supplier.city if supplier and supplier.city else "Bengaluru"
        category = supplier.category if supplier and supplier.category else "FMCG Distribution"
        gstin = supplier.gstin if supplier else None

        # Catalog items
        catalog = []
        if supplier:
            catalog_rows = (
                await self.session.execute(
                    select(SupplierProduct, Product)
                    .join(Product, Product.id == SupplierProduct.product_id)
                    .where(SupplierProduct.supplier_id == supplier.id)
                    .limit(10)
                )
            ).tuples()
            catalog = [
                {
                    "name": prod.name,
                    "sku": prod.sku,
                    "supplier_sku": sp.supplier_sku,
                    "unit": prod.unit,
                    "price": float(sp.unit_price),
                    "available_quantity": float(sp.available_quantity),
                    "lead_time_days": sp.lead_time_days,
                }
                for sp, prod in catalog_rows
            ]

        # Incoming orders
        incoming_orders = []
        if supplier:
            orders = list(
                await self.session.scalars(
                    select(Order)
                    .where(Order.supplier_id == supplier.id)
                    .order_by(Order.created_at.desc())
                    .limit(5)
                )
            )
            for o in orders:
                merchant_row = await self.session.get(Merchant, o.merchant_id)
                incoming_orders.append(
                    {
                        "order_id": str(o.id),
                        "merchant_name": merchant_row.name if merchant_row else "Kirana Store",
                        "total_amount": float(o.total_amount),
                        "status": o.status,
                        "created_at": o.created_at.isoformat(),
                    }
                )

        return {
            "account_type": "supplier",
            "business_name": supplier_name,
            "city": city,
            "category": category,
            "gstin": gstin,
            "trust_score": float(supplier.trust_score)
            if supplier and supplier.trust_score
            else 0.95,
            "catalog_items": catalog,
            "incoming_orders": incoming_orders,
            "pending_orders_count": sum(
                1
                for o in incoming_orders
                if o["status"] in {OrderStatus.APPROVAL_PENDING, OrderStatus.PROPOSED}
            ),
        }

    async def get_grounding_prompt(self, merchant_id: UUID, *, role: str = "merchant") -> str:
        """Formats live business context into a structured grounding prompt for LLM generation."""
        data = await self.get_business_context(merchant_id, role=role)

        if data["account_type"] == "supplier":
            catalog_lines = (
                "\n".join(
                    f"  - {c['name']} (SKU: {c['sku']}): ₹{c['price']}/{c['unit']}, Available: {c['available_quantity']} {c['unit']}"
                    for c in data["catalog_items"]
                )
                if data["catalog_items"]
                else "  (No catalog items listed yet)"
            )
            orders_lines = (
                "\n".join(
                    f"  - Order {o['order_id'][:8]} from {o['merchant_name']}: ₹{o['total_amount']} [{o['status']}]"
                    for o in data["incoming_orders"]
                )
                if data["incoming_orders"]
                else "  (No incoming purchase orders)"
            )
            return (
                f"### LIVE SUPPLIER BUSINESS GROUNDING:\n"
                f"- Supplier Name: {data['business_name']}\n"
                f"- Hub City: {data['city']} | Category: {data['category']}\n"
                f"- GSTIN: {data.get('gstin') or 'Not Registered'}\n"
                f"- Trust Score: {data['trust_score'] * 100:.0f}%\n"
                f"- Pending Orders to Fulfill: {data['pending_orders_count']}\n"
                f"Catalog Items:\n{catalog_lines}\n"
                f"Recent Orders:\n{orders_lines}\n"
            )

        # Merchant grounding
        inventory_items = data.get("inventory_items", [])
        inventory_lines = (
            "\n".join(
                f"  - {item['name']} (SKU: {item['sku']}): {item['quantity_on_hand']} {item['unit']} in stock (reorder threshold: {item['reorder_point']} {item['unit']})"
                for item in inventory_items
            )
            if inventory_items
            else "  (No inventory items recorded)"
        )

        low_stock_lines = (
            "\n".join(
                f"  - {item['name']}: {item['quantity_on_hand']} {item['unit']} in stock (reorder threshold: {item['reorder_point']} {item['unit']}, deficit: {item['deficit']:.1f})"
                for item in data["low_stock_items"]
            )
            if data["low_stock_items"]
            else "  (No items currently below reorder threshold)"
        )

        pending_approval_lines = (
            "\n".join(
                f"  - Approval {a['approval_id'][:8]} (Proposal: {a['proposal_id'][:8]}): {a['quantity']} {a['unit']} {a['sku']} @ ₹{a['unit_price']} (Total: ₹{a['total_amount']})"
                for a in data["pending_approvals"]
            )
            if data["pending_approvals"]
            else "  (No pending purchase proposals waiting for approval)"
        )

        recent_inventory_lines = (
            "\n".join(
                f"  - {event['event_type']} {event['name']}: {event['quantity_delta']:+g} {event['unit']} "
                f"via {event['source']} (now {event['quantity_after']:g})"
                for event in data.get("recent_inventory_events", [])
            )
            or "  (No recent inventory changes)"
        )
        recent_transaction_lines = (
            "\n".join(
                f"  - Transaction {txn['transaction_id'][:8]}: ₹{txn['amount']:,.2f} [{txn['status']}]"
                for txn in data.get("recent_transactions", [])
            )
            or "  (No procurement transactions recorded)"
        )

        top_cust_lines = (
            ", ".join(f"{c['name']} (₹{c['total_spent']:.0f})" for c in data["top_customers"])
            if data["top_customers"]
            else "None recorded"
        )

        return (
            f"### LIVE STORE BUSINESS GROUNDING:\n"
            f"- Store Name: {data['business_name']} ({data['business_type']})\n"
            f"- Location: {data['store_address']}\n"
            f"- GSTIN: {data.get('gstin') or 'Not Registered'} | PAN: {data.get('pan') or 'None'}\n"
            f"- Total Products: {data['total_products']} | Total Inventory Valuation: ₹{data['total_inventory_value']:,.2f}\n"
            f"- Today's Sales: ₹{data['today_sales_amount']:,.2f} across {data['today_sales_count']} bills\n"
            f"- Procurement Transactions: {data['transaction_count']} (settled ₹{data['successful_transaction_amount']:,.2f}, pending ₹{data['pending_transaction_amount']:,.2f})\n"
            f"- Settlement: Expected today ₹{data['expected_settlement']:,.2f} into {data['bank_name']} (A/c ending {data['account_ending']}), Yesterday settled: ₹{data['yesterday_settled']:,.2f}\n"
            f"- Registered Customers: {data['total_customers']} (Top: {top_cust_lines})\n"
            f"Available Inventory Products ({len(inventory_items)} items):\n{inventory_lines}\n"
            f"Recent Inventory Changes:\n{recent_inventory_lines}\n"
            f"Recent Procurement Transactions:\n{recent_transaction_lines}\n"
            f"Low Stock Items Requiring Attention ({data['low_stock_count']}):\n{low_stock_lines}\n"
            f"Pending Autonomous Purchase Proposals ({len(data['pending_approvals'])}):\n{pending_approval_lines}\n"
        )
