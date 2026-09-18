"""Add authentication, activity, notification, and realtime contracts.

Revision ID: 0002_merchant_contracts
Revises: 0001_initial
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_merchant_contracts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.add_column(
        "users",
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("is_phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column("negotiations", sa.Column("store_id", sa.Uuid(), nullable=True))
    op.add_column(
        "negotiations", sa.Column("workflow_request_id", sa.String(128), nullable=True)
    )
    op.add_column("negotiations", sa.Column("proposal_id", sa.Uuid(), nullable=True))
    op.add_column("negotiations", sa.Column("current_quote", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_negotiations_store_id",
        "negotiations",
        "stores",
        ["store_id"],
        ["id"],
        postgresql_not_valid=True,
    )
    op.add_column("a2a_agents", sa.Column("supplier_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_a2a_agents_supplier_id",
        "a2a_agents",
        "suppliers",
        ["supplier_id"],
        ["id"],
        postgresql_not_valid=True,
    )

    for column in (
        sa.Column("merchant_id", sa.Uuid(), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("negotiation_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="RECORDED"),
    ):
        op.add_column("a2a_messages", column)
    op.create_foreign_key(
        "fk_a2a_messages_merchant_id",
        "a2a_messages",
        "merchants",
        ["merchant_id"],
        ["id"],
        postgresql_not_valid=True,
    )
    op.create_foreign_key(
        "fk_a2a_messages_supplier_id",
        "a2a_messages",
        "suppliers",
        ["supplier_id"],
        ["id"],
        postgresql_not_valid=True,
    )
    op.create_foreign_key(
        "fk_a2a_messages_order_id",
        "a2a_messages",
        "orders",
        ["order_id"],
        ["id"],
        postgresql_not_valid=True,
    )
    op.create_foreign_key(
        "fk_a2a_messages_negotiation_id",
        "a2a_messages",
        "negotiations",
        ["negotiation_id"],
        ["id"],
        postgresql_not_valid=True,
    )

    op.add_column("outbox_events", sa.Column("merchant_id", sa.Uuid(), nullable=True))
    op.add_column("outbox_events", sa.Column("correlation_id", sa.String(128), nullable=True))
    op.add_column(
        "outbox_events",
        sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_foreign_key(
        "fk_outbox_events_merchant_id",
        "outbox_events",
        "merchants",
        ["merchant_id"],
        ["id"],
        postgresql_not_valid=True,
    )

    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Uuid(), sa.ForeignKey("refresh_sessions.id")),
        sa.Column("device_name", sa.String(120), nullable=True),
        *_timestamps(),
    )
    op.create_table(
        "otp_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("identifier", sa.String(320), nullable=False),
        sa.Column("identifier_hash", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("otp_hash", sa.String(255), nullable=False),
        sa.Column("request_ip_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resend_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("resend_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_resends", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_table(
        "oauth_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("nonce_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_table(
        "oauth_identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_subject", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("provider", "provider_subject"),
        sa.UniqueConstraint("user_id", "provider"),
    )
    op.create_table(
        "order_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("merchant_id", sa.Uuid(), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("merchant_id", sa.Uuid(), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )

    indexes = [
        ("ix_negotiations_merchant_status_created", "negotiations", ["merchant_id", "status", "created_at"]),
        ("ix_a2a_messages_merchant_created", "a2a_messages", ["merchant_id", "created_at"]),
        ("ix_outbox_pending_created", "outbox_events", ["published_at", "created_at"]),
        ("ix_refresh_sessions_user_expires", "refresh_sessions", ["user_id", "expires_at"]),
        ("ix_otp_identifier_created", "otp_challenges", ["identifier_hash", "created_at"]),
        ("ix_otp_expiry_consumed", "otp_challenges", ["expires_at", "consumed_at"]),
        ("ix_oauth_challenge_expiry", "oauth_challenges", ["expires_at", "consumed_at"]),
        ("ix_order_events_order_created", "order_events", ["order_id", "created_at"]),
        ("ix_notifications_merchant_read_created", "notifications", ["merchant_id", "is_read", "created_at"]),
    ]
    with op.get_context().autocommit_block():
        for name, table, columns in indexes:
            op.create_index(name, table, columns, postgresql_concurrently=True)


def downgrade() -> None:
    indexes = [
        ("ix_notifications_merchant_read_created", "notifications"),
        ("ix_order_events_order_created", "order_events"),
        ("ix_oauth_challenge_expiry", "oauth_challenges"),
        ("ix_otp_expiry_consumed", "otp_challenges"),
        ("ix_otp_identifier_created", "otp_challenges"),
        ("ix_refresh_sessions_user_expires", "refresh_sessions"),
        ("ix_outbox_pending_created", "outbox_events"),
        ("ix_a2a_messages_merchant_created", "a2a_messages"),
        ("ix_negotiations_merchant_status_created", "negotiations"),
    ]
    with op.get_context().autocommit_block():
        for name, table in indexes:
            op.drop_index(name, table_name=table, postgresql_concurrently=True)
    for table in (
        "notifications",
        "order_events",
        "oauth_identities",
        "oauth_challenges",
        "otp_challenges",
        "refresh_sessions",
    ):
        op.drop_table(table)
    op.drop_constraint("fk_outbox_events_merchant_id", "outbox_events", type_="foreignkey")
    op.drop_column("outbox_events", "event_version")
    op.drop_column("outbox_events", "correlation_id")
    op.drop_column("outbox_events", "merchant_id")
    for constraint in (
        "fk_a2a_messages_negotiation_id",
        "fk_a2a_messages_order_id",
        "fk_a2a_messages_supplier_id",
        "fk_a2a_messages_merchant_id",
    ):
        op.drop_constraint(constraint, "a2a_messages", type_="foreignkey")
    for column in ("status", "negotiation_id", "order_id", "supplier_id", "merchant_id"):
        op.drop_column("a2a_messages", column)
    op.drop_constraint("fk_a2a_agents_supplier_id", "a2a_agents", type_="foreignkey")
    op.drop_column("a2a_agents", "supplier_id")
    op.drop_constraint("fk_negotiations_store_id", "negotiations", type_="foreignkey")
    for column in ("current_quote", "proposal_id", "workflow_request_id", "store_id"):
        op.drop_column("negotiations", column)
    op.drop_column("users", "is_phone_verified")
    op.drop_column("users", "is_email_verified")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
