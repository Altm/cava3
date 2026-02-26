"""migrate recipes to ingredient model

Revision ID: 20260220_100000
Revises: 20260219_090000
Create Date: 2026-02-20 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260220_100000"
down_revision = "20260219_090000"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


def _has_column(table: str, column: str) -> bool:
    return any(col["name"] == column for col in _inspector().get_columns(table))


def _drop_fk_by_column(table: str, constrained_column: str) -> None:
    bind = op.get_bind()
    for fk in _inspector().get_foreign_keys(table):
        columns = fk.get("constrained_columns") or []
        if constrained_column in columns and fk.get("name"):
            try:
                op.drop_constraint(fk["name"], table, type_="foreignkey")
            except Exception:
                if bind.dialect.name != "postgresql":
                    continue


def upgrade() -> None:
    if not _has_table("ingredient"):
        op.create_table(
            "ingredient",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("base_unit_id", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["base_unit_id"], ["unit.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", name="uq_ingredient_code"),
        )

    if not _has_table("ingredient_product_binding"):
        op.create_table(
            "ingredient_product_binding",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("ingredient_id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("ratio_to_ingredient_base", sa.DECIMAL(18, 6), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("location_id", sa.Integer(), nullable=True),
            sa.Column("valid_from", sa.DateTime(), nullable=True),
            sa.Column("valid_to", sa.DateTime(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["ingredient_id"], ["ingredient.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint("ratio_to_ingredient_base > 0", name="ck_ingredient_binding_ratio_positive"),
            sa.CheckConstraint("priority >= 0", name="ck_ingredient_binding_priority_non_negative"),
            sa.UniqueConstraint(
                "ingredient_id",
                "product_id",
                "location_id",
                "valid_from",
                name="uq_ingredient_binding_scope",
            ),
        )

    if _has_table("product_recipe_component") and not _has_column("product_recipe_component", "ingredient_id"):
        op.add_column("product_recipe_component", sa.Column("ingredient_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_product_recipe_component_ingredient_id",
            "product_recipe_component",
            "ingredient",
            ["ingredient_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    if _has_table("product_recipe_component") and _has_column("product_recipe_component", "component_product_id"):
        source_queries = ["SELECT prc.component_product_id, prc.unit_id FROM product_recipe_component prc"]
        if _has_table("product_composite"):
            source_queries.append("SELECT pc.component_product_id, pc.unit_id FROM product_composite pc")
        source_union = "\n                UNION\n                ".join(source_queries)
        op.execute(
            f"""
            INSERT INTO ingredient (code, name, base_unit_id, description, is_active, created_at, updated_at)
            SELECT DISTINCT
                CONCAT('ing_', src.component_product_id, '_', src.unit_id) AS code,
                CONCAT(p.name, ' (', u.code, ')') AS name,
                src.unit_id AS base_unit_id,
                CONCAT('Migrated from product #', p.id) AS description,
                true,
                now(),
                now()
            FROM (
                {source_union}
            ) src
            JOIN product p ON p.id = src.component_product_id
            JOIN unit u ON u.id = src.unit_id
            WHERE NOT EXISTS (
                SELECT 1 FROM ingredient i
                WHERE i.code = CONCAT('ing_', src.component_product_id, '_', src.unit_id)
            )
            """
        )

        op.execute(
            """
            INSERT INTO ingredient_product_binding (
                ingredient_id,
                product_id,
                ratio_to_ingredient_base,
                priority,
                location_id,
                valid_from,
                valid_to,
                is_active,
                created_at,
                updated_at
            )
            SELECT
                i.id AS ingredient_id,
                src.component_product_id AS product_id,
                ratio.ratio_to_ingredient_base,
                100,
                NULL,
                NULL,
                NULL,
                true,
                now(),
                now()
            FROM (
                SELECT DISTINCT prc.component_product_id, prc.unit_id
                FROM product_recipe_component prc
            ) src
            JOIN product p ON p.id = src.component_product_id
            JOIN ingredient i ON i.code = CONCAT('ing_', src.component_product_id, '_', src.unit_id)
            LEFT JOIN product_unit pu
                ON pu.product_id = src.component_product_id
               AND pu.unit_id = src.unit_id
            LEFT JOIN product_type_unit ptu
                ON ptu.product_type_id = p.product_type_id
               AND ptu.unit_id = src.unit_id
            CROSS JOIN LATERAL (
                SELECT
                    CASE
                        WHEN src.unit_id = p.base_unit_id THEN 1::numeric
                        WHEN pu.ratio_to_base IS NOT NULL AND pu.ratio_to_base > 0 THEN 1::numeric / pu.ratio_to_base
                        WHEN ptu.ratio_to_base IS NOT NULL AND ptu.ratio_to_base > 0 THEN 1::numeric / ptu.ratio_to_base
                        ELSE 0::numeric
                    END AS ratio_to_ingredient_base
            ) ratio
            WHERE ratio.ratio_to_ingredient_base > 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM ingredient_product_binding b
                  WHERE b.ingredient_id = i.id
                    AND b.product_id = src.component_product_id
                    AND b.location_id IS NULL
                    AND b.valid_from IS NULL
              )
            """
        )

        op.execute(
            """
            UPDATE product_recipe_component prc
            SET ingredient_id = i.id
            FROM ingredient i
            WHERE i.code = CONCAT('ing_', prc.component_product_id, '_', prc.unit_id)
              AND prc.ingredient_id IS NULL
            """
        )

        op.execute(
            """
            UPDATE ingredient_product_binding b
            SET ratio_to_ingredient_base = 1
            WHERE b.ratio_to_ingredient_base <= 0
            """
        )

    if _has_table("product_recipe_component") and _has_column("product_recipe_component", "ingredient_id"):
        op.alter_column("product_recipe_component", "ingredient_id", nullable=False)

    if _has_table("product_recipe_component") and _has_column("product_recipe_component", "component_product_id"):
        _drop_fk_by_column("product_recipe_component", "component_product_id")
        op.drop_column("product_recipe_component", "component_product_id")

    if _has_table("product_composite"):
        op.drop_table("product_composite")


def downgrade() -> None:
    if not _has_table("product_composite"):
        op.create_table(
            "product_composite",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("parent_product_id", sa.Integer(), nullable=False),
            sa.Column("component_product_id", sa.Integer(), nullable=False),
            sa.Column("quantity", sa.DECIMAL(18, 6), nullable=False),
            sa.Column("unit_id", sa.Integer(), nullable=False),
            sa.Column("substitution_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("rounding", sa.String(length=32), nullable=True),
            sa.Column("waste_factor", sa.DECIMAL(6, 4), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["parent_product_id"], ["product.id"]),
            sa.ForeignKeyConstraint(["component_product_id"], ["product.id"]),
            sa.ForeignKeyConstraint(["unit_id"], ["unit.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("parent_product_id", "component_product_id", name="uq_component_unique"),
        )

    if _has_table("product_recipe_component") and not _has_column("product_recipe_component", "component_product_id"):
        op.add_column("product_recipe_component", sa.Column("component_product_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_product_recipe_component_component_product_id",
            "product_recipe_component",
            "product",
            ["component_product_id"],
            ["id"],
        )
        op.execute(
            """
            UPDATE product_recipe_component prc
            SET component_product_id = sub.product_id
            FROM (
                SELECT DISTINCT ON (b.ingredient_id)
                    b.ingredient_id,
                    b.product_id
                FROM ingredient_product_binding b
                WHERE b.is_active = true
                ORDER BY b.ingredient_id, b.priority ASC, b.id ASC
            ) sub
            WHERE sub.ingredient_id = prc.ingredient_id
            """
        )
        op.alter_column("product_recipe_component", "component_product_id", nullable=False)
        _drop_fk_by_column("product_recipe_component", "ingredient_id")
        op.drop_column("product_recipe_component", "ingredient_id")

    if _has_table("ingredient_product_binding"):
        op.drop_table("ingredient_product_binding")
    if _has_table("ingredient"):
        op.drop_table("ingredient")
