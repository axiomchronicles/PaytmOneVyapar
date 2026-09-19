"""Add customer, settlement entities and gstin, pan, location columns.

Revision ID: 0005_business_entities
Revises: 0004_timestamp_defaults
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_business_entities"
down_revision = "0004_timestamp_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to merchants
    op.add_column("merchants", sa.Column("gstin", sa.String(20), nullable=True))
    op.add_column("merchants", sa.Column("pan", sa.String(20), nullable=True))
    op.add_column(
        "merchants",
        sa.Column("business_type", sa.String(50), nullable=False, server_default="retail"),
    )
    op.create_index("ix_merchants_gstin", "merchants", ["gstin"])

    # Add columns to suppliers
    op.add_column("suppliers", sa.Column("phone_number", sa.String(30), nullable=True))
    op.add_column("suppliers", sa.Column("gstin", sa.String(20), nullable=True))
    op.add_column("suppliers", sa.Column("pan", sa.String(20), nullable=True))
    op.add_column("suppliers", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("suppliers", sa.Column("state", sa.String(100), nullable=True))
    op.add_column("suppliers", sa.Column("pincode", sa.String(20), nullable=True))
    op.add_column(
        "suppliers",
        sa.Column("address", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column("suppliers", sa.Column("category", sa.String(100), nullable=True))
    op.create_index("ix_suppliers_city", "suppliers", ["city"])
    op.create_index("ix_suppliers_pincode", "suppliers", ["pincode"])

    # Create customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "merchant_id",
            sa.Uuid(),
            sa.ForeignKey("merchants.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone_number", sa.String(30), nullable=False, index=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("address", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("total_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_spent",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("last_visit", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("merchant_id", "phone_number", name="uq_customers_merchant_phone"),
    )

    # Create settlements table
    op.create_table(
        "settlements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "merchant_id",
            sa.Uuid(),
            sa.ForeignKey("merchants.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "store_id",
            sa.Uuid(),
            sa.ForeignKey("stores.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column(
            "status",
            sa.String(40),
            nullable=False,
            server_default="PROCESSING",
        ),
        sa.Column("utr", sa.String(100), nullable=True, index=True),
        sa.Column("bank_name", sa.String(100), nullable=False, server_default="HDFC Bank"),
        sa.Column("account_ending", sa.String(10), nullable=False, server_default="4921"),
        sa.Column(
            "settlement_time",
            sa.String(50),
            nullable=False,
            server_default="by 4:00 PM",
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index(
        "ix_settlements_merchant_created",
        "settlements",
        ["merchant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_settlements_merchant_created", table_name="settlements")
    op.drop_table("settlements")
    op.drop_table("customers")
    op.drop_index("ix_suppliers_pincode", table_name="suppliers")
    op.drop_index("ix_suppliers_city", table_name="suppliers")
    op.drop_column("suppliers", "category")
    op.drop_column("suppliers", "address")
    op.drop_column("suppliers", "pincode")
    op.drop_column("suppliers", "state")
    op.drop_column("suppliers", "city")
    op.drop_column("suppliers", "pan")
    op.drop_column("suppliers", "gstin")
    op.drop_column("suppliers", "phone_number")
    op.drop_index("ix_merchants_gstin", table_name="merchants")
    op.drop_column("merchants", "business_type")
    op.drop_column("merchants", "pan")
    op.drop_column("merchants", "gstin")
