"""Add server timestamp defaults to new contract tables.

Revision ID: 0004_timestamp_defaults
Revises: 0003_contract_indexes
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_timestamp_defaults"
down_revision = "0003_contract_indexes"
branch_labels = None
depends_on = None

TABLES = (
    "refresh_sessions",
    "otp_challenges",
    "oauth_challenges",
    "oauth_identities",
    "order_events",
    "notifications",
)


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(
            table,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        )
        op.alter_column(
            table,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        )


def downgrade() -> None:
    for table in TABLES:
        op.alter_column(
            table,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
        )
        op.alter_column(
            table,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
        )
