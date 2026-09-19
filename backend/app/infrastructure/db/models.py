from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import ApprovalStatus, OrderStatus, TransactionStatus
from app.infrastructure.db.base import Base, Timestamped, UUIDPrimaryKey


class User(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "users"

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="merchant")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)


class Merchant(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "merchants"

    name: Mapped[str] = mapped_column(String(200))
    phone_number: Mapped[str | None] = mapped_column(String(30), unique=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    spending_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    gstin: Mapped[str | None] = mapped_column(String(20), index=True)
    pan: Mapped[str | None] = mapped_column(String(20))
    business_type: Mapped[str] = mapped_column(String(50), default="retail")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Store(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("merchant_id", "name"),)

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    address: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    @property
    def city(self) -> str | None:
        if isinstance(self.address, dict):
            return self.address.get("city")
        return None

    @property
    def state(self) -> str | None:
        if isinstance(self.address, dict):
            return self.address.get("state")
        return None

    @property
    def pincode(self) -> str | None:
        if isinstance(self.address, dict):
            return self.address.get("pincode") or self.address.get("postal_code")
        return None

    @property
    def address_line1(self) -> str | None:
        if isinstance(self.address, dict):
            return self.address.get("address_line1") or self.address.get("street") or self.address.get("flat")
        return None


class Product(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("merchant_id", "sku"),)

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    sku: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(30))
    category: Mapped[str | None] = mapped_column(String(100))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Inventory(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("store_id", "product_id"),)

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), index=True)
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)

    @property
    def safety_stock(self) -> Decimal:
        return Decimal("0")


class InventoryEvent(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "inventory_events"
    __table_args__ = (
        UniqueConstraint("merchant_id", "idempotency_key"),
        Index("ix_inventory_events_store_product_created", "store_id", "product_id", "created_at"),
    )

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    quantity_after: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    source: Mapped[str] = mapped_column(String(50))
    idempotency_key: Mapped[str] = mapped_column(String(128), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Sale(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "sales"
    __table_args__ = (Index("ix_sales_store_product_sold", "store_id", "product_id", "sold_at"),)

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    signals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Customer(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("merchant_id", "phone_number"),)

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    phone_number: Mapped[str] = mapped_column(String(30), index=True)
    email: Mapped[str | None] = mapped_column(String(320))
    address: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    last_visit: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Supplier(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "suppliers"

    merchant_id: Mapped[UUID | None] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    adapter_type: Mapped[str] = mapped_column(String(40), default="rest")
    endpoint: Mapped[str | None] = mapped_column(String(500))
    trust_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    phone_number: Mapped[str | None] = mapped_column(String(30))
    gstin: Mapped[str | None] = mapped_column(String(20))
    pan: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    state: Mapped[str | None] = mapped_column(String(100))
    pincode: Mapped[str | None] = mapped_column(String(20), index=True)
    address: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    category: Mapped[str | None] = mapped_column(String(100))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class SupplierProduct(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "supplier_products"
    __table_args__ = (UniqueConstraint("supplier_id", "product_id"),)

    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id"), index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), index=True)
    supplier_sku: Mapped[str] = mapped_column(String(100), index=True)
    available_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    lead_time_days: Mapped[int] = mapped_column(Integer, default=1)


class Order(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("merchant_id", "idempotency_key"),
        UniqueConstraint("proposal_id"),
        UniqueConstraint("order_hash"),
        Index("ix_orders_merchant_status_created", "merchant_id", "status", "created_at"),
    )

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id"), index=True)
    proposal_id: Mapped[UUID] = mapped_column(index=True)
    approval_id: Mapped[UUID | None] = mapped_column(ForeignKey("approvals.id"), index=True)
    order_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), default=OrderStatus.PROPOSED, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    idempotency_key: Mapped[str] = mapped_column(String(128), index=True)
    supplier_reference: Mapped[str | None] = mapped_column(String(200))
    failure_reason: Mapped[str | None] = mapped_column(Text)


class OrderItem(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "order_items"

    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id"), index=True)
    sku: Mapped[str] = mapped_column(String(100), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit: Mapped[str] = mapped_column(String(30))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class Negotiation(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "negotiations"
    __table_args__ = (
        Index("ix_negotiations_merchant_status_created", "merchant_id", "status", "created_at"),
    )

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    store_id: Mapped[UUID | None] = mapped_column(ForeignKey("stores.id"), index=True)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id"), index=True)
    correlation_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    workflow_request_id: Mapped[str | None] = mapped_column(String(128), index=True)
    proposal_id: Mapped[UUID | None] = mapped_column(index=True)
    sku: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    round_count: Mapped[int] = mapped_column(Integer, default=0)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    current_quote: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class AgentSession(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "agent_sessions"

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    store_id: Mapped[UUID | None] = mapped_column(ForeignKey("stores.id"), index=True)
    thread_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    channel: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), index=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AgentMessage(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "agent_messages"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("agent_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(30))
    content: Mapped[str | None] = mapped_column(Text)
    structured_content: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    provider_message_id: Mapped[str | None] = mapped_column(String(200), unique=True)


class AgentRun(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "agent_runs"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("agent_sessions.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    current_node: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class Approval(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "approvals"
    __table_args__ = (
        UniqueConstraint("proposal_id", "order_hash"),
        UniqueConstraint("nonce"),
        Index("ix_approvals_merchant_status_created", "merchant_id", "status", "created_at"),
    )

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    proposal_id: Mapped[UUID] = mapped_column(index=True)
    workflow_request_id: Mapped[str | None] = mapped_column(String(128), index=True)
    order_hash: Mapped[str] = mapped_column(String(64), index=True)
    proposal_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default=ApprovalStatus.PENDING, index=True)
    nonce: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(String(40), default="API")
    revision: Mapped[int] = mapped_column(Integer, default=1)


class Transaction(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("order_id"),
        UniqueConstraint("merchant_id", "idempotency_key"),
    )

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    approval_id: Mapped[UUID] = mapped_column(ForeignKey("approvals.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(40), default=TransactionStatus.PENDING, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(200))
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class Settlement(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "settlements"
    __table_args__ = (Index("ix_settlements_merchant_created", "merchant_id", "created_at"),)

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    store_id: Mapped[UUID | None] = mapped_column(ForeignKey("stores.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(40), default="PROCESSING")
    utr: Mapped[str | None] = mapped_column(String(100), index=True)
    bank_name: Mapped[str] = mapped_column(String(100), default="HDFC Bank")
    account_ending: Mapped[str] = mapped_column(String(10), default="4921")
    settlement_time: Mapped[str] = mapped_column(String(50), default="by 4:00 PM")
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "audit_logs"

    merchant_id: Mapped[UUID | None] = mapped_column(ForeignKey("merchants.id"), index=True)
    actor_type: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[str] = mapped_column(String(200), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(200), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class A2AAgent(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "a2a_agents"

    name: Mapped[str] = mapped_column(String(200), unique=True)
    endpoint: Mapped[str] = mapped_column(String(500))
    public_key: Mapped[str | None] = mapped_column(Text)
    shared_secret_ref: Mapped[str | None] = mapped_column(String(200))
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"), index=True)
    allowed_intents: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class A2AMessage(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "a2a_messages"
    __table_args__ = (
        UniqueConstraint("message_id"),
        UniqueConstraint("sender_agent_id", "nonce"),
        UniqueConstraint("idempotency_key"),
        Index("ix_a2a_messages_correlation_created", "correlation_id", "created_at"),
        Index("ix_a2a_messages_merchant_created", "merchant_id", "created_at"),
    )

    merchant_id: Mapped[UUID | None] = mapped_column(ForeignKey("merchants.id"), index=True)
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"), index=True)
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id"), index=True)
    negotiation_id: Mapped[UUID | None] = mapped_column(ForeignKey("negotiations.id"), index=True)
    message_id: Mapped[UUID] = mapped_column(index=True)
    correlation_id: Mapped[UUID] = mapped_column(index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    sender_agent_id: Mapped[UUID] = mapped_column(index=True)
    receiver_agent_id: Mapped[UUID] = mapped_column(index=True)
    intent: Mapped[str] = mapped_column(String(80), index=True)
    direction: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40), default="RECORDED", index=True)
    nonce: Mapped[str] = mapped_column(String(128))
    idempotency_key: Mapped[str] = mapped_column(String(128), index=True)
    envelope: Mapped[dict[str, Any]] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VoiceSession(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "voice_sessions"

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    agent_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_sessions.id"), index=True
    )
    active_proposal_id: Mapped[UUID | None] = mapped_column(index=True)
    language_code: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    audio_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ChannelMessage(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "channel_messages"
    __table_args__ = (UniqueConstraint("channel", "provider_message_id"),)

    merchant_id: Mapped[UUID | None] = mapped_column(ForeignKey("merchants.id"), index=True)
    channel: Mapped[str] = mapped_column(String(40), index=True)
    direction: Mapped[str] = mapped_column(String(20))
    provider_message_id: Mapped[str] = mapped_column(String(250))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), index=True)
    message_type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), index=True)


class OutboxEvent(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_pending_created", "published_at", "created_at"),)

    merchant_id: Mapped[UUID | None] = mapped_column(ForeignKey("merchants.id"), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), index=True)
    aggregate_id: Mapped[UUID] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)


class IdempotencyKey(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("scope", "key"),)

    scope: Mapped[str] = mapped_column(String(100), index=True)
    key: Mapped[str] = mapped_column(String(128), index=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="PROCESSING")
    response: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class RefreshSession(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "refresh_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash"),
        Index("ix_refresh_sessions_user_expires", "user_id", "expires_at"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    replaced_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("refresh_sessions.id"))
    device_name: Mapped[str | None] = mapped_column(String(120))


class OtpChallenge(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "otp_challenges"
    __table_args__ = (
        Index("ix_otp_identifier_created", "identifier_hash", "created_at"),
        Index("ix_otp_expiry_consumed", "expires_at", "consumed_at"),
    )

    identifier: Mapped[str] = mapped_column(String(320))
    identifier_hash: Mapped[str] = mapped_column(String(64), index=True)
    purpose: Mapped[str] = mapped_column(String(30), index=True)
    otp_hash: Mapped[str] = mapped_column(String(255))
    request_ip_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    resend_available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    resend_count: Mapped[int] = mapped_column(Integer, default=0)
    max_resends: Mapped[int] = mapped_column(Integer, default=3)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class OAuthChallenge(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "oauth_challenges"
    __table_args__ = (Index("ix_oauth_challenge_expiry", "expires_at", "consumed_at"),)

    provider: Mapped[str] = mapped_column(String(30), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True)
    nonce_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class OAuthIdentity(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "oauth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject"),
        UniqueConstraint("user_id", "provider"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30), index=True)
    provider_subject: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320), index=True)


class OrderEvent(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "order_events"
    __table_args__ = (Index("ix_order_events_order_created", "order_id", "created_at"),)

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Notification(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_merchant_read_created", "merchant_id", "is_read", "created_at"),
    )

    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    notification_type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(80), index=True)
    entity_id: Mapped[UUID | None] = mapped_column(index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
