from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CursorPage[T](ContractModel):
    items: list[T]
    next_cursor: str | None = None


class OffsetPage[T](ContractModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class ApprovalView(ContractModel):
    id: UUID
    proposal_id: UUID
    workflow_request_id: str | None
    order_hash: str
    proposal: dict[str, Any]
    status: str
    revision: int
    expires_at: datetime
    decided_at: datetime | None
    created_at: datetime
    action_token: str | None = None


class OrderItemView(ContractModel):
    id: UUID
    sku: str
    quantity: Decimal
    unit: str
    unit_price: Decimal


class TimelineEvent(ContractModel):
    id: UUID
    status: str
    occurred_at: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class OrderView(ContractModel):
    id: UUID
    proposal_id: UUID
    approval_id: UUID | None
    store_id: UUID
    supplier_id: UUID
    supplier_name: str
    status: str
    total_amount: Decimal
    currency: str
    supplier_reference: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemView] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)


class SupplierProductView(ContractModel):
    id: UUID
    product_id: UUID
    supplier_sku: str
    product_name: str
    merchant_sku: str
    unit: str
    available_quantity: Decimal
    unit_price: Decimal
    lead_time_days: int


class SupplierCatalogUpsertRequest(ContractModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field(min_length=1, max_length=30)
    available_quantity: Decimal = Field(ge=0)
    unit_price: Decimal = Field(gt=0)
    lead_time_days: int = Field(default=1, ge=0, le=90)
    category: str | None = Field(default=None, max_length=100)
    supplier_sku: str | None = Field(default=None, max_length=100)


class SupplierOrderDecisionRequest(ContractModel):
    approved: bool
    idempotency_key: str = Field(min_length=8, max_length=128)


class SupplierView(ContractModel):
    id: UUID
    name: str
    adapter_type: str
    is_active: bool
    trust_score: Decimal
    product_count: int = 0
    phone_number: str | None = None
    gstin: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    category: str | None = None
    products: list[SupplierProductView] = Field(default_factory=list)


class NegotiationView(ContractModel):
    id: UUID
    store_id: UUID | None
    supplier_id: UUID
    supplier_name: str
    correlation_id: UUID
    workflow_request_id: str | None
    proposal_id: UUID | None
    approval_id: UUID | None = None
    sku: str
    status: str
    round_count: int
    constraints: dict[str, Any]
    history: list[dict[str, Any]]
    current_quote: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class StartNegotiationRequest(ContractModel):
    sku: str = Field(min_length=1, max_length=100)
    supplier_id: UUID | None = None
    store_id: UUID | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    target_price: Decimal | None = Field(default=None, gt=0)
    max_price: Decimal | None = Field(default=None, gt=0)


class A2AActivityView(ContractModel):
    id: UUID
    message_id: UUID
    correlation_id: UUID
    supplier_id: UUID | None
    order_id: UUID | None
    negotiation_id: UUID | None
    intent: str
    direction: str
    status: str
    summary: str
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class ActivityView(ContractModel):
    id: UUID
    action: str
    actor_type: str
    resource_type: str
    resource_id: str
    trace_id: str | None
    metadata: dict[str, Any]
    occurred_at: datetime


class InventoryHistoryView(ContractModel):
    id: UUID
    store_id: UUID
    product_id: UUID
    event_type: str
    quantity_delta: Decimal
    quantity_after: Decimal
    source: str
    occurred_at: datetime


class NotificationView(ContractModel):
    id: UUID
    notification_type: str
    title: str
    body: str
    entity_type: str | None
    entity_id: UUID | None
    payload: dict[str, Any]
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class AnalyticsPoint(ContractModel):
    bucket: str
    value: Decimal


class AnalyticsBreakdown(ContractModel):
    key: str
    label: str
    value: Decimal
    entity_id: UUID | None = None


class DateRangeView(ContractModel):
    from_: datetime = Field(alias="from", serialization_alias="from")
    to: datetime


class OpportunityView(ContractModel):
    id: str
    title: str
    subtitle: str
    action_label: str
    action_type: str
    icon: str = "chart"


class CriticalAlertView(ContractModel):
    title: str
    description: str
    tag: str = "Dhyaan dene layak"
    sku: str = "COLD-COLA-300"
    action_label: str = "Review"
    action_url: str = "/recommendations"


class QuickActionView(ContractModel):
    id: str
    label: str
    icon: str
    target: str


class SettlementView(ContractModel):
    expected_today: Decimal
    currency: str = "INR"
    status: str = "Processing"
    settlement_time: str = "by 4:00 PM"
    bank_name: str = "HDFC Bank"
    account_ending: str = "4921"
    yesterday_settled: Decimal
    utr: str = "PAYTMUTR982341209"


class PaymentQRView(ContractModel):
    merchant_name: str
    store_name: str
    vpa: str
    soundbox_active: bool = True
    qr_string: str


class CampaignRequest(ContractModel):
    title: str
    discount_pct: Decimal = Decimal("5.0")
    target_audience: str = "all_customers"


class CampaignResponse(ContractModel):
    id: UUID
    title: str
    status: str
    audience_count: int
    created_at: datetime


class AnalyticsOverviewView(ContractModel):
    sales_quantity: Decimal
    low_inventory_products: int
    orders_by_status: dict[str, int]
    range: DateRangeView
    total_sales_amount: Decimal = Field(default=Decimal("0.00"))
    sales_growth_pct: Decimal = Field(default=Decimal("0.0"))
    customer_count: int = Field(default=0)
    customer_growth_pct: Decimal = Field(default=Decimal("0.0"))
    expected_settlement: Decimal = Field(default=Decimal("0.00"))
    critical_alert: CriticalAlertView | None = None
    opportunities: list[OpportunityView] = Field(default_factory=list)
    quick_actions: list[QuickActionView] = Field(default_factory=list)


class SalesAnalyticsView(ContractModel):
    metric: str
    currency: str
    group_by: str
    points: list[AnalyticsPoint]


class InventoryCategoryView(ContractModel):
    category: str
    products: int
    low_products: int


class InventoryAnalyticsView(ContractModel):
    categories: list[InventoryCategoryView]


class ProcurementSupplierView(ContractModel):
    supplier_id: UUID
    supplier_name: str
    order_count: int
    spend: Decimal


class ProcurementAnalyticsView(ContractModel):
    currency: str
    suppliers: list[ProcurementSupplierView]


class CustomerView(ContractModel):
    id: UUID
    merchant_id: UUID
    name: str
    phone_number: str
    email: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)
    total_orders: int = 0
    total_spent: Decimal = Decimal("0.00")
    last_visit: datetime | None = None
    created_at: datetime


class TransactionView(ContractModel):
    id: UUID
    merchant_id: UUID
    order_id: UUID
    approval_id: UUID
    amount: Decimal
    currency: str
    status: str
    idempotency_key: str
    provider_reference: str | None = None
    created_at: datetime


class SettlementDetailView(ContractModel):
    id: UUID
    merchant_id: UUID
    store_id: UUID | None = None
    amount: Decimal
    currency: str
    status: str
    utr: str | None = None
    bank_name: str
    account_ending: str
    settlement_time: str
    settled_at: datetime | None = None
    created_at: datetime


class NearbySupplierView(ContractModel):
    id: UUID
    name: str
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    locality: str | None = None
    distance_km: float | None = None
    trust_score: Decimal = Decimal("0.95")
    product_count: int = 0
    phone_number: str | None = None
    category: str | None = None


class NearbyMerchantView(ContractModel):
    id: UUID
    name: str
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    locality: str | None = None
    distance_km: float | None = None
    product_count: int = 0
    phone_number: str | None = None
    business_type: str = "retail"
