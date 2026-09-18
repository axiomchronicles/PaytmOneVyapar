from typing import Any, Literal, TypedDict


class PurchaseWorkflowState(TypedDict, total=False):
    merchant_id: str
    store_id: str
    request_id: str
    sku: str
    required_quantity: float
    unit: str
    target_price: float
    max_price: float
    spending_limit: float
    delivery_requirement: str
    inventory_snapshot: dict[str, Any]
    sales_history: list[dict[str, Any]]
    demand_forecast: dict[str, Any]
    candidate_suppliers: list[dict[str, Any]]
    selected_supplier: dict[str, Any]
    negotiation_history: list[dict[str, Any]]
    negotiated_price: float
    risk_result: dict[str, Any]
    proposal: dict[str, Any]
    proposal_revision: int
    order_hash: str
    approval_status: Literal["PENDING", "APPROVED", "MODIFIED", "REJECTED", "EXPIRED"]
    approval_id: str
    approval_token: str
    execution_status: str
    execution_result: dict[str, Any]
    failure_reason: str
    trace_id: str
    attempted_supplier_ids: list[str]
    merchant_quantity_override: bool
