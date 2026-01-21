"""add typed attributes and unit cost

Revision ID: 0002_simple_catalog
Revises: 0001_initial
Create Date: 2025-01-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_simple_catalog"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("product_type", sa.Column("is_composite", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("product", sa.Column("unit_cost", sa.DECIMAL(precision=18, scale=2), nullable=False, server_default="0"))

    op.create_table(
        "attribute_definition",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_type_id", sa.Integer(), sa.ForeignKey("product_type.id"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("data_type", sa.String(length=16), nullable=False),
        sa.Column("unit_code", sa.String(length=32), sa.ForeignKey("unit.code"), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("product_type_id", "code", name="uq_attrdef_producttype_code"),
        comment="Attribute definitions per product type",
    )

    op.create_table(
        "product_attribute_value",
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), primary_key=True),
        sa.Column("attribute_definition_id", sa.Integer(), sa.ForeignKey("attribute_definition.id"), primary_key=True),
        sa.Column("value_number", sa.DECIMAL(18, 6), nullable=True),
        sa.Column("value_boolean", sa.Boolean(), nullable=True),
        sa.Column("value_string", sa.String(length=255), nullable=True),
        comment="Typed attribute values per product",
    )


def downgrade():
    op.drop_table("product_attribute_value")
    op.drop_table("attribute_definition")
    op.drop_column("product", "unit_cost")
    op.drop_column("product_type", "is_composite")
