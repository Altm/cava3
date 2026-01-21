"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "unit",
        sa.Column("code", sa.String(length=32), primary_key=True, comment="Unit code, e.g. bottle, glass"),
        sa.Column("description", sa.String(length=255), nullable=False, comment="Human readable description"),
        sa.Column("ratio_to_base", sa.DECIMAL(18, 6), nullable=False, server_default="1", comment="Conversion ratio to base unit for this product group"),
        sa.Column("discrete_step", sa.DECIMAL(10, 6), nullable=True, comment="Optional discrete step to control fractional quantities"),
        comment="Unit table",
    )
    op.create_table(
        "unitconversion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("from_unit", sa.String(length=32), sa.ForeignKey("unit.code")),
        sa.Column("to_unit", sa.String(length=32), sa.ForeignKey("unit.code")),
        sa.Column("ratio", sa.DECIMAL(18, 6), nullable=False),
        sa.UniqueConstraint("from_unit", "to_unit", name="uq_unit_conversion"),
        comment="Unit conversions table",
    )
    op.create_table(
        "producttype",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=100), unique=True),
        sa.Column("description", sa.String(length=255)),
        comment="Product types table",
    )
    op.create_table(
        "product",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=64), unique=True),
        sa.Column("primary_category", sa.String(length=64), nullable=False),
        sa.Column("product_type_id", sa.Integer, sa.ForeignKey("producttype.id")),
        sa.Column("base_unit_code", sa.String(length=32), sa.ForeignKey("unit.code")),
        sa.Column("is_composite", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("tax_flags", sa.String(length=128)),
        comment="Product table",
    )
    op.create_table(
        "productcategory",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("product_id", "category", name="uq_product_category"),
        comment="Product categories table",
    )
    op.create_table(
        "productattribute",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("product_id", "name", name="uq_product_attribute"),
        comment="Product attributes table",
    )
    op.create_table(
        "compositecomponent",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("parent_product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("component_product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("quantity", sa.DECIMAL(18, 6), nullable=False),
        sa.Column("unit_code", sa.String(length=32), sa.ForeignKey("unit.code")),
        sa.Column("substitution_allowed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("rounding", sa.String(length=32)),
        sa.UniqueConstraint("parent_product_id", "component_product_id", name="uq_component_unique"),
        comment="Composite components table",
    )
    op.create_table(
        "location",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=128), unique=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        comment="Location table",
    )
    op.create_table(
        "stock",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id")),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("quantity", sa.DECIMAL(18, 6), nullable=False, server_default="0"),
        sa.Column("unit_code", sa.String(length=32), sa.ForeignKey("unit.code")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("location_id", "product_id", name="uq_stock_location_product"),
        sa.CheckConstraint("quantity >= 0", name="ck_stock_non_negative"),
        comment="Stock table",
    )
    op.create_table(
        "pricelist",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id")),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("unit_code", sa.String(length=32), sa.ForeignKey("unit.code")),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount", sa.DECIMAL(18, 2), nullable=False),
        sa.UniqueConstraint("location_id", "product_id", "unit_code", name="uq_price_location_product_unit"),
        comment="Price list table",
    )
    op.create_table(
        "terminal",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("terminal_id", sa.String(length=64), unique=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id")),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        comment="Terminals table",
    )
    op.create_table(
        "saleevent",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("event_id", sa.String(length=128), unique=True),
        sa.Column("terminal_id", sa.Integer, sa.ForeignKey("terminal.id")),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id")),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime),
        comment="Sale events table",
    )
    op.create_table(
        "saleline",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sale_event_id", sa.Integer, sa.ForeignKey("saleevent.id")),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("quantity", sa.DECIMAL(18, 6), nullable=False),
        sa.Column("unit_code", sa.String(length=32), sa.ForeignKey("unit.code")),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("price", sa.DECIMAL(18, 2), nullable=False),
        comment="Sale lines table",
    )
    op.create_table(
        "adjustment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id")),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("delta", sa.DECIMAL(18, 6), nullable=False),
        sa.Column("unit_code", sa.String(length=32), sa.ForeignKey("unit.code")),
        sa.Column("reason", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        comment="Adjustments table",
    )
    op.create_table(
        "transfer",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("from_location_id", sa.Integer, sa.ForeignKey("location.id")),
        sa.Column("to_location_id", sa.Integer, sa.ForeignKey("location.id")),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("quantity", sa.DECIMAL(18, 6), nullable=False),
        sa.Column("unit_code", sa.String(length=32), sa.ForeignKey("unit.code")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        comment="Transfers table",
    )
    op.create_table(
        "inventorysnapshot",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id")),
        sa.Column("taken_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("data", sa.JSON, nullable=False),
        comment="Inventory snapshots table",
    )
    op.create_table(
        "user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(length=64), unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default=sa.text("false")),
        comment="Users table",
    )
    op.create_table(
        "role",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=64), unique=True),
        sa.Column("scope", sa.String(length=16), nullable=False, server_default="global"),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("location.id")),
        comment="Roles table",
    )
    op.create_table(
        "permission",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(length=128), unique=True),
        sa.Column("description", sa.String(length=255)),
        comment="Permissions table",
    )
    op.create_table(
        "rolepermission",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("role.id")),
        sa.Column("permission_id", sa.Integer, sa.ForeignKey("permission.id")),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        comment="Role permissions table",
    )
    op.create_table(
        "userrole",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("role.id")),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        comment="User roles table",
    )
    op.create_table(
        "auditlog",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("model", sa.String(length=128)),
        sa.Column("record_id", sa.String(length=128)),
        sa.Column("action", sa.String(length=16)),
        sa.Column("old_data", sa.JSON),
        sa.Column("new_data", sa.JSON),
        sa.Column("actor", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        comment="Audit log table",
    )
    op.create_table(
        "requestlog",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.String(length=128)),
        sa.Column("method", sa.String(length=8)),
        sa.Column("path", sa.String(length=255)),
        sa.Column("status_code", sa.Integer),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.Column("terminal_id", sa.Integer, sa.ForeignKey("terminal.id")),
        sa.Column("context", sa.JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        comment="Request log table",
    )


def downgrade():
    tables = [
        "requestlog",
        "auditlog",
        "userrole",
        "rolepermission",
        "permission",
        "role",
        "user",
        "inventorysnapshot",
        "transfer",
        "adjustment",
        "saleline",
        "saleevent",
        "terminal",
        "pricelist",
        "stock",
        "location",
        "compositecomponent",
        "productattribute",
        "productcategory",
        "product",
        "producttype",
        "unitconversion",
        "unit",
    ]
    for table in tables:
        op.drop_table(table)
