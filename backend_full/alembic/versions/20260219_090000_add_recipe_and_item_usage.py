"""add recipe versioning, generic item usage and portion fields

Revision ID: 20260219_090000
Revises: 20260218_150000
Create Date: 2026-02-19 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260219_090000"
down_revision = "20260218_150000"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


def _has_column(table: str, column: str) -> bool:
    return any(col["name"] == column for col in _inspector().get_columns(table))


def _drop_constraint_if_exists(table: str, name: str, kind: str = "check") -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        row = bind.execute(
            sa.text(
                """
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE t.relname = :table_name
                  AND c.conname = :constraint_name
                """
            ),
            {"table_name": table, "constraint_name": name},
        ).first()
        if row:
            op.drop_constraint(name, table, type_=kind)
        return
    try:
        op.drop_constraint(name, table, type_=kind)
    except Exception:
        pass


def upgrade() -> None:
    if _has_table("product"):
        if not _has_column("product", "default_portion_size"):
            op.add_column("product", sa.Column("default_portion_size", sa.DECIMAL(18, 6), nullable=True))
        if not _has_column("product", "portions_per_unit"):
            op.add_column("product", sa.Column("portions_per_unit", sa.Integer(), nullable=True))

    if _has_table("product_composite") and not _has_column("product_composite", "waste_factor"):
        op.add_column(
            "product_composite",
            sa.Column(
                "waste_factor",
                sa.DECIMAL(6, 4),
                nullable=False,
                server_default="0",
                comment="Expected loss share for this component (0.05 = 5%)",
            ),
        )

    if not _has_table("product_recipe"):
        op.create_table(
            "product_recipe",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("valid_from", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("valid_to", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("product_id", "version", name="uq_product_recipe_product_version"),
        )

    if not _has_table("product_recipe_component"):
        op.create_table(
            "product_recipe_component",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("recipe_id", sa.Integer(), nullable=False),
            sa.Column("component_product_id", sa.Integer(), nullable=False),
            sa.Column("quantity", sa.DECIMAL(18, 6), nullable=False),
            sa.Column("unit_id", sa.Integer(), nullable=False),
            sa.Column("substitution_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("rounding", sa.String(length=32), nullable=True),
            sa.Column("waste_factor", sa.DECIMAL(6, 4), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["recipe_id"], ["product_recipe.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["component_product_id"], ["product.id"]),
            sa.ForeignKeyConstraint(["unit_id"], ["unit.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint("quantity > 0", name="ck_product_recipe_component_quantity_positive"),
            sa.CheckConstraint("waste_factor >= 0", name="ck_product_recipe_component_waste_non_negative"),
        )

    if _has_table("product_composite"):
        op.execute(
            """
            INSERT INTO product_recipe (product_id, version, is_active, valid_from, valid_to, created_by, created_at, updated_at)
            SELECT DISTINCT
                pc.parent_product_id,
                1,
                true,
                now(),
                CAST(NULL AS TIMESTAMP),
                CAST(NULL AS INTEGER),
                now(),
                now()
            FROM product_composite pc
            WHERE NOT EXISTS (
                SELECT 1 FROM product_recipe pr WHERE pr.product_id = pc.parent_product_id
            )
            """
        )
        op.execute(
            """
            INSERT INTO product_recipe_component (
                recipe_id, component_product_id, quantity, unit_id, substitution_allowed, rounding, waste_factor, created_at, updated_at
            )
            SELECT
                pr.id,
                pc.component_product_id,
                pc.quantity,
                pc.unit_id,
                COALESCE(pc.substitution_allowed, false),
                pc.rounding,
                COALESCE(pc.waste_factor, 0),
                now(),
                now()
            FROM product_composite pc
            JOIN product_recipe pr
              ON pr.product_id = pc.parent_product_id
             AND pr.version = 1
            LEFT JOIN product_recipe_component prc
              ON prc.recipe_id = pr.id
             AND prc.component_product_id = pc.component_product_id
             AND prc.unit_id = pc.unit_id
            WHERE prc.id IS NULL
            """
        )

    if _has_table("product_item_pour") and not _has_table("product_item_usage"):
        op.rename_table("product_item_pour", "product_item_usage")

    if _has_table("product_item_usage"):
        if _has_column("product_item_usage", "glasses_total") and not _has_column("product_item_usage", "total_units"):
            op.alter_column("product_item_usage", "glasses_total", new_column_name="total_units")
        if _has_column("product_item_usage", "glasses_sold") and not _has_column("product_item_usage", "used_units"):
            op.alter_column("product_item_usage", "glasses_sold", new_column_name="used_units")

        if _has_column("product_item_usage", "total_units"):
            op.alter_column(
                "product_item_usage",
                "total_units",
                existing_type=sa.Integer(),
                type_=sa.DECIMAL(18, 6),
                postgresql_using="total_units::numeric(18,6)",
                nullable=False,
            )
        if _has_column("product_item_usage", "used_units"):
            op.alter_column(
                "product_item_usage",
                "used_units",
                existing_type=sa.Integer(),
                type_=sa.DECIMAL(18, 6),
                postgresql_using="used_units::numeric(18,6)",
                nullable=False,
                existing_server_default="0",
                server_default="0",
            )

        if not _has_column("product_item_usage", "unit_id"):
            op.add_column("product_item_usage", sa.Column("unit_id", sa.Integer(), nullable=True))
        if not _has_column("product_item_usage", "metadata_json"):
            op.add_column("product_item_usage", sa.Column("metadata_json", sa.JSON(), nullable=True))

        op.execute(
            """
            UPDATE product_item_usage u
            SET unit_id = COALESCE(portion.unit_id, p.base_unit_id)
            FROM product_item pi
            JOIN product p ON p.id = pi.product_id
            LEFT JOIN LATERAL (
                SELECT pu.unit_id
                FROM product_unit pu
                JOIN unit un ON un.id = pu.unit_id
                WHERE pu.product_id = p.id
                  AND un.unit_type = 'portion'
                ORDER BY pu.ratio_to_base ASC, pu.unit_id ASC
                LIMIT 1
            ) AS portion ON TRUE
            WHERE u.product_item_id = pi.id
              AND u.unit_id IS NULL
            """
        )
        op.alter_column("product_item_usage", "unit_id", nullable=False)

        _drop_constraint_if_exists("product_item_usage", "ck_product_item_pour_total_positive")
        _drop_constraint_if_exists("product_item_usage", "ck_product_item_pour_sold_non_negative")
        _drop_constraint_if_exists("product_item_usage", "ck_product_item_pour_sold_le_total")
        _drop_constraint_if_exists("product_item_usage", "ck_product_item_usage_total_positive")
        _drop_constraint_if_exists("product_item_usage", "ck_product_item_usage_used_non_negative")
        _drop_constraint_if_exists("product_item_usage", "ck_product_item_usage_used_le_total")

        op.create_check_constraint("ck_product_item_usage_total_positive", "product_item_usage", "total_units > 0")
        op.create_check_constraint("ck_product_item_usage_used_non_negative", "product_item_usage", "used_units >= 0")
        op.create_check_constraint("ck_product_item_usage_used_le_total", "product_item_usage", "used_units <= total_units")
        op.create_foreign_key(
            "fk_product_item_usage_unit_id",
            "product_item_usage",
            "unit",
            ["unit_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    _drop_constraint_if_exists("product_item_usage", "fk_product_item_usage_unit_id", kind="foreignkey")
    _drop_constraint_if_exists("product_item_usage", "ck_product_item_usage_total_positive")
    _drop_constraint_if_exists("product_item_usage", "ck_product_item_usage_used_non_negative")
    _drop_constraint_if_exists("product_item_usage", "ck_product_item_usage_used_le_total")
    if _has_table("product_item_usage"):
        if _has_column("product_item_usage", "metadata_json"):
            op.drop_column("product_item_usage", "metadata_json")
        if _has_column("product_item_usage", "unit_id"):
            op.drop_column("product_item_usage", "unit_id")
        if _has_column("product_item_usage", "used_units") and not _has_column("product_item_usage", "glasses_sold"):
            op.alter_column("product_item_usage", "used_units", new_column_name="glasses_sold")
        if _has_column("product_item_usage", "total_units") and not _has_column("product_item_usage", "glasses_total"):
            op.alter_column("product_item_usage", "total_units", new_column_name="glasses_total")
        if _has_table("product_item_usage") and not _has_table("product_item_pour"):
            op.rename_table("product_item_usage", "product_item_pour")

    if _has_table("product_recipe_component"):
        op.drop_table("product_recipe_component")
    if _has_table("product_recipe"):
        op.drop_table("product_recipe")

    if _has_table("product_composite") and _has_column("product_composite", "waste_factor"):
        op.drop_column("product_composite", "waste_factor")
    if _has_table("product"):
        if _has_column("product", "portions_per_unit"):
            op.drop_column("product", "portions_per_unit")
        if _has_column("product", "default_portion_size"):
            op.drop_column("product", "default_portion_size")
