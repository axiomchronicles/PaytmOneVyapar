from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import AgentRunRequest
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import InvalidRequestError, NotFoundError
from app.domain.enums import AgentRunStatus
from app.infrastructure.db.models import (
    AgentRun,
    AgentSession,
    Inventory,
    Merchant,
    Product,
    Sale,
    Store,
)
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/agents", tags=["agents"])


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
