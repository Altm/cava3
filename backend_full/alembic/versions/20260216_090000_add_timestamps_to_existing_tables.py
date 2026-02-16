"""add created_at/updated_at to existing tables

Revision ID: 20260216_090000
Revises: 20260206_140000
Create Date: 2026-02-16 09:00:00.000000

Adds created_at and updated_at columns to all existing tables except:
audit_log, alembic_version, permission, request_log, role, user_role.

Also adds a DB trigger to maintain updated_at on UPDATE.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "20260216_090000"
down_revision = "20260206_140000"
branch_labels = None
depends_on = None


EXCLUDED_TABLES = {
    "audit_log",
    "alembic_version",
    "permission",
    "request_log",
    "role",
    "user_role",
}


def table_exists(table_name: str) -> bool:
    connection = op.get_bind()
    result = connection.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = :table_name
            )
            """
        ),
        {"table_name": table_name},
    )
    return bool(result.scalar())


def column_exists(table_name: str, column_name: str) -> bool:
    connection = op.get_bind()
    result = connection.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                  AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return bool(result.scalar())


def ensure_timestamp_columns(table_name: str) -> None:
    if table_name in EXCLUDED_TABLES:
        return
    if not table_exists(table_name):
        return

    if not column_exists(table_name, "created_at"):
        op.add_column(
            table_name,
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
                comment="Row creation timestamp",
            ),
        )
    if not column_exists(table_name, "updated_at"):
        op.add_column(
            table_name,
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
                comment="Row update timestamp (auto-maintained)",
            ),
        )

    # Backfill just in case (covers nullable legacy columns)
    if column_exists(table_name, "created_at") and column_exists(table_name, "updated_at"):
        quote = op.get_bind().dialect.identifier_preparer.quote
        table_sql = quote(table_name)
        op.execute(
            sa.text(
                f"""
                UPDATE {table_sql}
                SET created_at = COALESCE(created_at, now()),
                    updated_at = COALESCE(updated_at, COALESCE(created_at, now()))
                """
            )
        )


def ensure_updated_at_trigger(table_name: str) -> None:
    if table_name in EXCLUDED_TABLES:
        return
    if not table_exists(table_name):
        return
    if not column_exists(table_name, "updated_at"):
        return
    quote = op.get_bind().dialect.identifier_preparer.quote
    trigger_name = f"trg_set_updated_at_{table_name}"
    trigger_sql = quote(trigger_name)
    table_sql = quote(table_name)
    op.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_sql} ON {table_sql}"))
    op.execute(
        sa.text(
            f"""
            CREATE TRIGGER {trigger_sql}
            BEFORE UPDATE ON {table_sql}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )
    )


def upgrade() -> None:
    # Shared trigger function for updated_at
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    tables = [
        # core catalog
        "unit",
        "product_type",
        "product",
        "product_category",
        "product_attribute_old",
        "product_attribute",
        "product_attribute_value",
        "product_unit",
        "product_composite",
        "product_meta",
        # locations and pricing
        "location",
        "price_list",
        # stock and movements
        "stock",
        "adjustment",
        "transfer",
        "inventory_snapshot",
        # sales and terminals
        "terminal",
        "sale_event",
        "sale_line",
        # auth
        "user",
        "role_permission",
    ]

    for table in tables:
        ensure_timestamp_columns(table)

    for table in tables:
        ensure_updated_at_trigger(table)


def downgrade() -> None:
    # Drop triggers first
    connection = op.get_bind()
    result = connection.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_name = 'updated_at'
            """
        )
    )
    for (table_name,) in result.fetchall():
        if table_name in EXCLUDED_TABLES:
            continue
        quote = op.get_bind().dialect.identifier_preparer.quote
        trigger_name = f"trg_set_updated_at_{table_name}"
        trigger_sql = quote(trigger_name)
        table_sql = quote(table_name)
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_sql} ON {table_sql}"))

    # Intentionally do not drop timestamp columns in downgrade.
    # Some tables had created_at-like columns before this migration, and
    # dropping them would be destructive. This project does not rely on downgrades.
