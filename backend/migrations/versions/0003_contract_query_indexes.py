"""Add indexes required by merchant contract query paths.

Revision ID: 0003_contract_indexes
Revises: 0002_merchant_contracts
"""

from alembic import op

revision = "0003_contract_indexes"
down_revision = "0002_merchant_contracts"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_a2a_agents_supplier_id", "a2a_agents", ["supplier_id"]),
    ("ix_a2a_messages_merchant_id", "a2a_messages", ["merchant_id"]),
    ("ix_a2a_messages_negotiation_id", "a2a_messages", ["negotiation_id"]),
    ("ix_a2a_messages_order_id", "a2a_messages", ["order_id"]),
    ("ix_a2a_messages_status", "a2a_messages", ["status"]),
    ("ix_a2a_messages_supplier_id", "a2a_messages", ["supplier_id"]),
    ("ix_negotiations_proposal_id", "negotiations", ["proposal_id"]),
    ("ix_negotiations_store_id", "negotiations", ["store_id"]),
    ("ix_negotiations_workflow_request_id", "negotiations", ["workflow_request_id"]),
    ("ix_notifications_created_at", "notifications", ["created_at"]),
    ("ix_notifications_entity_id", "notifications", ["entity_id"]),
    ("ix_notifications_entity_type", "notifications", ["entity_type"]),
    ("ix_notifications_is_read", "notifications", ["is_read"]),
    ("ix_notifications_merchant_id", "notifications", ["merchant_id"]),
    ("ix_notifications_notification_type", "notifications", ["notification_type"]),
    ("ix_notifications_user_id", "notifications", ["user_id"]),
    ("ix_oauth_challenges_consumed_at", "oauth_challenges", ["consumed_at"]),
    ("ix_oauth_challenges_created_at", "oauth_challenges", ["created_at"]),
    ("ix_oauth_challenges_expires_at", "oauth_challenges", ["expires_at"]),
    ("ix_oauth_challenges_provider", "oauth_challenges", ["provider"]),
    ("ix_oauth_identities_created_at", "oauth_identities", ["created_at"]),
    ("ix_oauth_identities_email", "oauth_identities", ["email"]),
    ("ix_oauth_identities_provider", "oauth_identities", ["provider"]),
    ("ix_oauth_identities_user_id", "oauth_identities", ["user_id"]),
    ("ix_order_events_created_at", "order_events", ["created_at"]),
    ("ix_order_events_merchant_id", "order_events", ["merchant_id"]),
    ("ix_order_events_order_id", "order_events", ["order_id"]),
    ("ix_order_events_status", "order_events", ["status"]),
    ("ix_otp_challenges_consumed_at", "otp_challenges", ["consumed_at"]),
    ("ix_otp_challenges_created_at", "otp_challenges", ["created_at"]),
    ("ix_otp_challenges_expires_at", "otp_challenges", ["expires_at"]),
    ("ix_otp_challenges_identifier_hash", "otp_challenges", ["identifier_hash"]),
    ("ix_otp_challenges_purpose", "otp_challenges", ["purpose"]),
    ("ix_otp_challenges_request_ip_hash", "otp_challenges", ["request_ip_hash"]),
    ("ix_outbox_events_correlation_id", "outbox_events", ["correlation_id"]),
    ("ix_outbox_events_merchant_id", "outbox_events", ["merchant_id"]),
    ("ix_refresh_sessions_created_at", "refresh_sessions", ["created_at"]),
    ("ix_refresh_sessions_expires_at", "refresh_sessions", ["expires_at"]),
    ("ix_refresh_sessions_merchant_id", "refresh_sessions", ["merchant_id"]),
    ("ix_refresh_sessions_revoked_at", "refresh_sessions", ["revoked_at"]),
    ("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"]),
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, columns in INDEXES:
            op.create_index(
                name,
                table,
                columns,
                postgresql_concurrently=True,
                if_not_exists=True,
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, _ in reversed(INDEXES):
            op.drop_index(
                name,
                table_name=table,
                postgresql_concurrently=True,
                if_exists=True,
            )
