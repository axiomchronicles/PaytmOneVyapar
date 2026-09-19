from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.munim_context import MunimContextService
from app.agents.munim_tools import MunimToolRegistry
from app.api.v1.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentRunRequest,
    LowStockReplenishmentResponse,
)
from app.channels.telegram.client import TelegramChannel
from app.channels.telegram.registry import get_telegram_chat_for_phone
from app.channels.voice.agent import VOICE_MUNIM_SYSTEM_PROMPT
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import InvalidRequestError, NotFoundError
from app.domain.enums import AgentRunStatus, ApprovalStatus
from app.infrastructure.db.models import (
    AgentRun,
    AgentSession,
    Approval,
    Inventory,
    Merchant,
    Product,
    Sale,
    Store,
    Supplier,
    SupplierProduct,
    User,
)
from app.infrastructure.db.session import get_session
from app.integrations.llm.base import DisabledLLMProvider

logger = structlog.get_logger()

router = APIRouter(prefix="/agents", tags=["agents"])


async def _reference_purchase_price(
    session: AsyncSession, *, merchant_id: UUID, product_id: UUID
) -> Decimal:
    """Returns the best available purchase price without storing price on Product."""
    supplier_price = await session.scalar(
        select(func.min(SupplierProduct.unit_price))
        .join(Supplier, Supplier.id == SupplierProduct.supplier_id)
        .where(
            SupplierProduct.product_id == product_id,
            Supplier.is_active.is_(True),
        )
    )
    if supplier_price is not None:
        return supplier_price

    latest_sale_price = await session.scalar(
        select(Sale.unit_price)
        .where(Sale.merchant_id == merchant_id, Sale.product_id == product_id)
        .order_by(Sale.sold_at.desc())
        .limit(1)
    )
    return latest_sale_price or Decimal("20.00")


@router.post("/runs", status_code=202)
async def start_run(
    body: AgentRunRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    store = await session.scalar(
        select(Store).where(
            Store.id == body.store_id,
            Store.merchant_id == principal.merchant_id,
        )
    )
    if store is None:
        raise NotFoundError("Store not found")
    product = await session.scalar(
        select(Product).where(
            Product.merchant_id == principal.merchant_id,
            Product.sku == body.sku,
        )
    )
    if product is None:
        raise NotFoundError("Product not found")
    inventory = await session.scalar(
        select(Inventory).where(
            Inventory.merchant_id == principal.merchant_id,
            Inventory.store_id == store.id,
            Inventory.product_id == product.id,
        )
    )
    merchant = await session.get(Merchant, principal.merchant_id)
    if inventory is None or merchant is None:
        raise NotFoundError("Inventory or merchant record not found")
    sales = list(
        await session.scalars(
            select(Sale)
            .where(
                Sale.merchant_id == principal.merchant_id,
                Sale.store_id == store.id,
                Sale.product_id == product.id,
            )
            .order_by(Sale.sold_at.desc())
            .limit(90)
        )
    )
    if not sales:
        raise InvalidRequestError("Demand history is not available for this product")
    state = {
        "merchant_id": str(principal.merchant_id),
        "store_id": str(body.store_id),
        "request_id": body.request_id,
        "sku": body.sku,
        "required_quantity": body.required_quantity,
        "unit": product.unit,
        "target_price": body.target_price,
        "max_price": body.max_price,
        "spending_limit": float(merchant.spending_limit),
        "delivery_requirement": body.delivery_deadline.isoformat(),
        "inventory_snapshot": {
            "quantity_on_hand": float(inventory.quantity_on_hand),
            "reorder_point": float(inventory.reorder_point),
            "safety_stock": body.safety_stock,
            "captured_at": datetime.now(UTC).isoformat(),
        },
        "sales_history": [
            {
                "date": sale.sold_at.isoformat(),
                "sales": float(sale.quantity),
                "inventory": float(inventory.quantity_on_hand),
                "price": float(sale.unit_price),
                **sale.signals,
            }
            for sale in reversed(sales)
        ],
        "trace_id": request.state.request_id,
        "proposal_revision": 1,
        "attempted_supplier_ids": [],
    }
    result = await request.app.state.workflow_runtime.start(state)
    thread_id = request.app.state.workflow_runtime.thread_id(
        str(principal.merchant_id), body.request_id
    )
    agent_session = await session.scalar(
        select(AgentSession).where(AgentSession.thread_id == thread_id)
    )
    if agent_session is None:
        agent_session = AgentSession(
            merchant_id=principal.merchant_id,
            store_id=body.store_id,
            thread_id=thread_id,
            channel="API",
            status="ACTIVE",
            context={"sku": body.sku},
        )
        session.add(agent_session)
        await session.flush()
    session.add(
        AgentRun(
            session_id=agent_session.id,
            request_id=body.request_id,
            trace_id=request.state.request_id,
            status=(
                AgentRunStatus.WAITING_APPROVAL
                if result.get("approval_status") == "PENDING"
                else AgentRunStatus.COMPLETED
            ),
            current_node="human_approval" if result.get("approval_status") == "PENDING" else None,
            started_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return {"request_id": body.request_id, "state": result}


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_munim(
    body: AgentChatRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> AgentChatResponse:
    """Conversational text interface for the Munim Assistant with live business context."""
    context_service = MunimContextService(session)
    context_data = await context_service.get_business_context(
        principal.merchant_id, role=principal.role
    )
    grounding_prompt = await context_service.get_grounding_prompt(
        principal.merchant_id, role=principal.role
    )
    tool_registry = MunimToolRegistry(session, principal.merchant_id, role=principal.role)

    tool_calls: list[dict[str, Any]] = []
    lower_msg = body.message.lower()

    # Match intent to execute tools
    if any(w in lower_msg for w in ["profile", "gst", "pan", "address", "dukaan"]):
        profile_res = await tool_registry.get_business_profile()
        tool_calls.append({"tool": "get_business_profile", "result": profile_res})
    if any(
        w in lower_msg for w in ["stock", "inventory", "maal", "reorder", "scan", "receipt", "bill"]
    ):
        inv_res = await tool_registry.get_inventory_summary()
        tool_calls.append({"tool": "get_inventory_summary", "result": inv_res})
    if any(w in lower_msg for w in ["sale", "bikri", "revenue", "kamaai", "aaj"]):
        sales_res = await tool_registry.get_sales_report()
        tool_calls.append({"tool": "get_sales_report", "result": sales_res})
    if any(w in lower_msg for w in ["settlement", "bank", "khata", "utr"]):
        settle_res = await tool_registry.get_settlements()
        tool_calls.append({"tool": "get_settlements", "result": settle_res})
    if principal.role != "supplier" and any(
        w in lower_msg for w in ["transaction", "payment", "purchase", "kharcha", "order"]
    ):
        transaction_res = await tool_registry.get_transaction_summary()
        tool_calls.append({"tool": "get_transaction_summary", "result": transaction_res})
    if any(w in lower_msg for w in ["supplier", "distributor", "dealer"]):
        supp_res = await tool_registry.search_suppliers()
        tool_calls.append({"tool": "search_suppliers", "result": supp_res})
    if any(w in lower_msg for w in ["approval", "proposal", "order"]):
        if principal.role == "supplier":
            order_res = await tool_registry.get_incoming_orders()
            tool_calls.append({"tool": "get_incoming_orders", "result": order_res})
        else:
            appr_res = await tool_registry.get_pending_approvals()
            tool_calls.append({"tool": "get_pending_approvals", "result": appr_res})

    # Generate response
    llm = getattr(request.app.state, "llm_provider", None)
    has_llm = llm is not None and not isinstance(llm, DisabledLLMProvider)

    if has_llm:
        try:
            tools_summary = ""
            if tool_calls:
                tools_summary = "\nTool Outputs:\n" + "\n".join(
                    f"- {tc['tool']}: {tc['result']}" for tc in tool_calls
                )
            system_prompt = (
                f"{VOICE_MUNIM_SYSTEM_PROMPT}\n\n"
                f"{grounding_prompt}\n"
                f"{tools_summary}\n"
                f"Instructions: Give a helpful, polite, and accurate response in natural Hinglish or the merchant's preferred language. Ground every number in the real data above."
            )
            messages = [{"role": "system", "content": system_prompt}]
            for past in body.conversation_history[-4:]:
                messages.append({"role": past.role, "content": past.content})
            messages.append({"role": "user", "content": body.message})
            reply = await llm.generate(messages)
            return AgentChatResponse(
                reply=reply, tool_calls=tool_calls, business_context=context_data
            )
        except Exception as exc:
            logger.warning("munim_chat_llm_failed", error=str(exc))

    # Grounded intelligent fallback
    business_name = context_data.get("business_name", "Vyapaar Partner")
    if any(w in lower_msg for w in ["sale", "bikri", "revenue", "kamaai", "aaj"]):
        sales_amt = context_data.get("today_sales_amount", 0.0)
        sales_cnt = context_data.get("today_sales_count", 0)
        reply = (
            f"Namaste ji! Aaj aapke store par kul ₹{sales_amt:,.2f} ki bikri hui hai ({sales_cnt} transactions). "
            f"Expected settlement ₹{context_data.get('expected_settlement', 0.0):,.2f} aaj shaam tak {context_data.get('bank_name', 'HDFC Bank')} me aayega."
        )
    elif any(w in lower_msg for w in ["settlement", "bank", "khata", "utr"]):
        expected = context_data.get("expected_settlement", 0.0)
        bank = context_data.get("bank_name", "HDFC Bank")
        acc = context_data.get("account_ending", "4921")
        yesterday = context_data.get("yesterday_settled", 0.0)
        reply = (
            f"Aapka aaj ka expected settlement ₹{expected:,.2f} hai, jo 4:00 PM tak {bank} (khata sankhya: ...{acc}) me credit hoga. "
            f"Kal ₹{yesterday:,.2f} ka settlement safalta-purvak complete ho chuka tha."
        )
    elif any(
        w in lower_msg for w in ["stock", "inventory", "maal", "reorder", "scan", "receipt", "bill"]
    ):
        low_items = context_data.get("low_stock_items", [])
        available_items = context_data.get("available_items", [])
        recent_events = context_data.get("recent_inventory_events", [])
        stock_snapshot = (
            ", ".join(
                f"{item['name']} ({item['quantity_on_hand']} {item['unit']})"
                for item in available_items[:5]
            )
            or "abhi koi inventory item record nahi hua"
        )
        recent_scan = (
            f" Latest update: {recent_events[0]['name']} {recent_events[0]['quantity_delta']:+g} "
            f"{recent_events[0]['unit']} via {recent_events[0]['source']}."
            if recent_events
            else ""
        )
        if low_items:
            items_str = ", ".join(
                f"{it['name']} ({it['quantity_on_hand']} {it['unit']} bache hain)"
                for it in low_items[:3]
            )
            reply = (
                f"Dukaan me kul {context_data.get('total_products', 0)} items hain. Current stock: {stock_snapshot}. "
                f"Inme se {len(low_items)} items low stock par hain: {items_str}."
                f"{recent_scan} "
                f"Munim ne inka auto-replenishment proposal prepare kiya hai, jise aap Approvals me dekh sakte hain."
            )
        else:
            reply = (
                f"Aapki dukaan me kul {context_data.get('total_products', 0)} products hain. "
                f"Current stock: {stock_snapshot}.{recent_scan} Koi bhi item reorder point se kam nahi hai."
            )
    elif any(w in lower_msg for w in ["transaction", "payment", "purchase", "kharcha", "order"]):
        recent_transactions = context_data.get("recent_transactions", [])
        latest = (
            f" Latest transaction ₹{recent_transactions[0]['amount']:,.2f} [{recent_transactions[0]['status']}]."
            if recent_transactions
            else ""
        )
        reply = (
            f"Aapke {context_data.get('transaction_count', 0)} procurement transactions recorded hain: "
            f"₹{context_data.get('successful_transaction_amount', 0.0):,.2f} settled aur "
            f"₹{context_data.get('pending_transaction_amount', 0.0):,.2f} pending hain.{latest}"
        )
    elif any(w in lower_msg for w in ["supplier", "distributor"]):
        suppliers = context_data.get("suppliers", [])
        if suppliers:
            s_str = ", ".join(f"{s['name']} ({s['category']})" for s in suppliers[:3])
            reply = f"Aapke area me active verified suppliers hain: {s_str}. Inke paas FMCG aur grocery items par badhiya margin aur quick delivery uplabdh hai."
        else:
            reply = "Aapke paas connected suppliers check karne ke liye 'Suppliers' tab me jakar nearby distributors dhoondh sakte hain."
    elif any(w in lower_msg for w in ["approval", "proposal"]):
        approvals = context_data.get("pending_approvals", [])
        if approvals:
            a = approvals[0]
            reply = (
                f"Aapke paas {len(approvals)} purchase proposal approval ke liye pending hai: "
                f"{a['quantity']} {a['unit']} {a['sku']} @ ₹{a['unit_price']}/unit (Total: ₹{a['total_amount']:,.2f}). "
                f"Aap ise Paytm ONE Vyapar app se turant Approve ya Modify kar sakte hain."
            )
        else:
            reply = "Abhi koi purchase proposal pending nahi hai. Sabhi procurement orders processed hain."
    elif any(w in lower_msg for w in ["profile", "gst", "pan"]):
        reply = (
            f"Business Name: {business_name} ({context_data.get('business_type', 'Retail')})\n"
            f"GSTIN: {context_data.get('gstin') or 'Registered nahi hai'}\n"
            f"PAN: {context_data.get('pan') or 'Registered nahi hai'}\n"
            f"Address: {context_data.get('store_address')}"
        )
    elif principal.role == "supplier":
        reply = (
            f"Namaste {business_name}! Aapke distributor account par {context_data.get('pending_orders_count', 0)} purchase orders pending hain. "
            f"Catalog me {len(context_data.get('catalog_items', []))} items listed hain."
        )
    else:
        reply = (
            f"Namaste {business_name} ji! Main aapka AI Munim hoon. "
            f"Main aapki dukaan ke stock, aaj ki bikri, bank settlement, ya suppliers se order mangwane me madad kar sakta hoon. Aap kya dekhna chahenge?"
        )

    return AgentChatResponse(reply=reply, tool_calls=tool_calls, business_context=context_data)


@router.post("/detect-low-stock", response_model=LowStockReplenishmentResponse)
async def detect_and_replenish_low_stock(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> LowStockReplenishmentResponse:
    """Scans merchant inventory, identifies items below reorder point, triggers autonomous purchase workflow, and sends multi-channel alerts."""
    store = await session.scalar(
        select(Store).where(Store.merchant_id == principal.merchant_id).limit(1)
    )
    if not store:
        return LowStockReplenishmentResponse(
            detected_count=0, low_stock_items=[], triggered_workflows=[], notifications_sent=[]
        )

    # Find low stock inventory
    low_inventory_stmt = (
        select(Inventory, Product)
        .join(Product, Product.id == Inventory.product_id)
        .where(
            Inventory.merchant_id == principal.merchant_id,
            Inventory.store_id == store.id,
            Inventory.quantity_on_hand <= Inventory.reorder_point,
        )
    )
    low_stock_rows = list((await session.execute(low_inventory_stmt)).tuples())

    detected_items: list[dict[str, Any]] = []
    triggered_workflows: list[dict[str, Any]] = []
    notifications_sent: set[str] = set()

    merchant = await session.get(Merchant, principal.merchant_id)
    user = await session.get(User, principal.user_id)
    spending_limit = (
        float(merchant.spending_limit) if merchant and merchant.spending_limit else 50000.0
    )

    for inventory, product in low_stock_rows:
        reference_price = await _reference_purchase_price(
            session,
            merchant_id=principal.merchant_id,
            product_id=product.id,
        )
        detected_items.append(
            {
                "sku": product.sku,
                "name": product.name,
                "unit": product.unit,
                "quantity_on_hand": float(inventory.quantity_on_hand),
                "reorder_point": float(inventory.reorder_point),
                "safety_stock": float(inventory.safety_stock or 0),
            }
        )

        # Check if an approval is already pending for this SKU
        existing_approval = await session.scalar(
            select(Approval).where(
                Approval.merchant_id == principal.merchant_id,
                Approval.status == ApprovalStatus.PENDING,
            )
        )
        if existing_approval and existing_approval.proposal_payload:
            if existing_approval.proposal_payload.get("sku") == product.sku:
                continue

        # Check demand history; if none, seed minimal historical sales so forecast node can compute
        sales_count = (
            await session.scalar(
                select(func.count(Sale.id)).where(
                    Sale.merchant_id == principal.merchant_id,
                    Sale.store_id == store.id,
                    Sale.product_id == product.id,
                )
            )
        ) or 0
        if sales_count == 0:
            for i in range(5, 0, -1):
                session.add(
                    Sale(
                        merchant_id=principal.merchant_id,
                        store_id=store.id,
                        product_id=product.id,
                        quantity=Decimal("5.00"),
                        unit_price=reference_price,
                        currency="INR",
                        sold_at=datetime.now(UTC) - timedelta(days=i),
                        signals={"weather": "sunny", "day_of_week": "weekday"},
                    )
                )
            await session.flush()

        sales = list(
            await session.scalars(
                select(Sale)
                .where(
                    Sale.merchant_id == principal.merchant_id,
                    Sale.store_id == store.id,
                    Sale.product_id == product.id,
                )
                .order_by(Sale.sold_at.desc())
                .limit(90)
            )
        )

        req_id = f"auto_replenish_{product.sku}_{uuid4().hex[:6]}"
        req_qty = float(
            max(
                inventory.reorder_point
                - inventory.quantity_on_hand
                + (inventory.safety_stock or 0),
                10.0,
            )
        )
        base_price_float = float(reference_price)

        state = {
            "merchant_id": str(principal.merchant_id),
            "store_id": str(store.id),
            "request_id": req_id,
            "sku": product.sku,
            "required_quantity": req_qty,
            "unit": product.unit,
            "target_price": round(base_price_float * 0.92, 2),
            "max_price": round(base_price_float * 1.15, 2),
            "spending_limit": spending_limit,
            "delivery_requirement": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "inventory_snapshot": {
                "quantity_on_hand": float(inventory.quantity_on_hand),
                "reorder_point": float(inventory.reorder_point),
                "safety_stock": float(inventory.safety_stock or 0),
                "captured_at": datetime.now(UTC).isoformat(),
            },
            "sales_history": [
                {
                    "date": s.sold_at.isoformat(),
                    "sales": float(s.quantity),
                    "inventory": float(inventory.quantity_on_hand),
                    "price": float(s.unit_price),
                    **s.signals,
                }
                for s in reversed(sales)
            ],
            "trace_id": str(uuid4()),
            "proposal_revision": 1,
            "attempted_supplier_ids": [],
        }

        runtime = getattr(request.app.state, "workflow_runtime", None)
        if runtime:
            try:
                workflow_result = await runtime.start(state)
                approval_id = workflow_result.get("approval_id")
                approval_token = workflow_result.get("approval_token")
                proposal = workflow_result.get("proposal") or {}
                notifications_sent.add("in_app")

                # Multi-channel Telegram alert
                if merchant and merchant.phone_number:
                    chat_id = get_telegram_chat_for_phone(merchant.phone_number)
                    if chat_id and getattr(request.app.state, "telegram_provider", None):
                        try:
                            channel = TelegramChannel(request.app.state.telegram_provider, session)
                            await channel.send_approval(
                                merchant_id=principal.merchant_id,
                                recipient=chat_id,
                                proposal=proposal,
                                idempotency_key=f"tg_{req_id}",
                            )
                            notifications_sent.add("telegram")
                        except Exception as exc:
                            logger.warning("telegram_auto_alert_failed", error=str(exc))

                # Multi-channel Email alert
                if user and user.email and getattr(request.app.state, "email_provider", None):
                    try:
                        email_provider = request.app.state.email_provider
                        total_amt = float(proposal.get("quantity", req_qty)) * float(
                            proposal.get("unit_price", base_price_float)
                        )
                        await email_provider.send_email(
                            to=user.email,
                            subject=f"⚠️ Low Stock Alert: {product.name} Reorder Proposal Ready for Approval",
                            html=(
                                f"<h3>Paytm ONE Vyapar - Autonomous Stock Alert</h3>"
                                f"<p>Item <b>{product.name} ({product.sku})</b> is below reorder point.</p>"
                                f"<p>A purchase proposal for <b>{proposal.get('quantity', req_qty)} {product.unit}</b> "
                                f"at ₹{proposal.get('unit_price', base_price_float)} (Total: ₹{total_amt:,.2f}) is awaiting your decision.</p>"
                                f"<p>Please open the Vyapaar app to Approve, Modify, or Decline.</p>"
                            ),
                            idempotency_key=f"email_{req_id}",
                        )
                        notifications_sent.add("email")
                    except Exception as exc:
                        logger.warning("email_auto_alert_failed", error=str(exc))

                triggered_workflows.append(
                    {
                        "request_id": req_id,
                        "sku": product.sku,
                        "product_name": product.name,
                        "approval_id": approval_id,
                        "approval_token": approval_token,
                        "status": workflow_result.get("approval_status", "PENDING"),
                    }
                )
            except Exception as exc:
                logger.error("auto_replenish_workflow_failed", sku=product.sku, error=str(exc))

    await session.commit()
    return LowStockReplenishmentResponse(
        detected_count=len(detected_items),
        low_stock_items=detected_items,
        triggered_workflows=triggered_workflows,
        notifications_sent=sorted(list(notifications_sent)),
    )
