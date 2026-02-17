"""add price list revision history tables

Revision ID: 20260218_090000
Revises: 20260217_180000
Create Date: 2026-02-18 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260218_090000"
down_revision = "20260217_180000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "price_list_revision",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False, comment="Target location"),
        sa.Column("name", sa.String(length=255), nullable=True, comment="Human-readable revision name"),
        sa.Column("mode", sa.String(length=32), nullable=False, comment="Generation mode: percent|fixed|calculator"),
        sa.Column("percent_delta", sa.Numeric(10, 4), nullable=True, comment="Percent delta for mode=percent"),
        sa.Column("amount_delta", sa.DECIMAL(18, 2), nullable=True, comment="Fixed amount delta for mode=fixed"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD", comment="Currency code"),
        sa.Column(
            "calculator_file",
            sa.String(length=255),
            nullable=True,
            comment="Calculator file path (relative to pricing calculators folder)",
        ),
        sa.Column("calculator_class", sa.String(length=255), nullable=True, comment="Calculator class name"),
        sa.Column("calculator_params", sa.JSON(), nullable=True, comment="Calculator params payload"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True, comment="User who created this revision"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "mode in ('percent','fixed','calculator')",
            name="ck_price_list_revision_mode",
        ),
    )
    op.create_index("ix_price_list_revision_location_created", "price_list_revision", ["location_id", "created_at"])

    op.create_table(
        "price_list_revision_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.Integer(), nullable=False, comment="Revision header reference"),
        sa.Column("product_id", sa.Integer(), nullable=False, comment="Product reference"),
        sa.Column("unit_id", sa.Integer(), nullable=False, comment="Unit reference"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD", comment="Currency code"),
        sa.Column("previous_amount", sa.DECIMAL(18, 2), nullable=True, comment="Amount before recalculation"),
        sa.Column("amount", sa.DECIMAL(18, 2), nullable=False, comment="Calculated amount"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["price_list_revision.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["unit.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "revision_id",
            "product_id",
            "unit_id",
            name="uq_price_list_revision_item_unique",
        ),
    )
    op.create_index("ix_price_list_revision_item_revision_id", "price_list_revision_item", ["revision_id"])


def downgrade() -> None:
    op.drop_index("ix_price_list_revision_item_revision_id", table_name="price_list_revision_item")
    op.drop_table("price_list_revision_item")
    op.drop_index("ix_price_list_revision_location_created", table_name="price_list_revision")
    op.drop_table("price_list_revision")
