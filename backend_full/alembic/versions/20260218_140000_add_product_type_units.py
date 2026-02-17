"""add product_type_unit defaults and strict mode

Revision ID: 20260218_140000
Revises: 20260218_130000
Create Date: 2026-02-18 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260218_140000"
down_revision = "20260218_130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_type",
        sa.Column(
            "strict_units_by_type",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="Allow only units defined at product type level",
        ),
    )

    op.create_table(
        "product_type_unit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_type_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("ratio_to_base", sa.DECIMAL(18, 6), nullable=False, comment="Ratio relative to product base unit"),
        sa.Column("discrete_step", sa.DECIMAL(10, 6), nullable=True, comment="Step for fractional quantities"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_type_id"], ["product_type.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["unit.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_type_id", "unit_id", name="uq_product_type_unit_product_type_unit"),
        sa.CheckConstraint("ratio_to_base > 0", name="ck_product_type_unit_positive_ratio"),
    )

    op.execute(
        """
        INSERT INTO product_unit (product_id, unit_id, ratio_to_base, discrete_step, created_at, updated_at)
        SELECT p.id, p.base_unit_id, 1, NULL, now(), now()
        FROM product p
        LEFT JOIN product_unit pu
          ON pu.product_id = p.id
         AND pu.unit_id = p.base_unit_id
        WHERE pu.id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_table("product_type_unit")
    op.drop_column("product_type", "strict_units_by_type")
