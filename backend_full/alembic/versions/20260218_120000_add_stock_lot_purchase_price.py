"""add purchase_price to stock_lot

Revision ID: 20260218_120000
Revises: 20260218_090000
Create Date: 2026-02-18 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260218_120000"
down_revision = "20260218_090000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stock_lot",
        sa.Column(
            "purchase_price",
            sa.DECIMAL(18, 2),
            nullable=True,
            comment="Purchase price fixed for lot at receipt generation",
        ),
    )
    op.execute(
        """
        UPDATE stock_lot
        SET purchase_price = product.base_cost
        FROM product
        WHERE product.id = stock_lot.product_id
          AND stock_lot.purchase_price IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("stock_lot", "purchase_price")
