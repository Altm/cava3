"""add box quantity and product_item_pour for glass sales

Revision ID: 20260217_120000
Revises: 20260216_100000
Create Date: 2026-02-17 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260217_120000"
down_revision = "20260216_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "box",
        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Current number of items in box",
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE box b
            SET quantity = COALESCE(src.cnt, 0)
            FROM (
                SELECT box_id, COUNT(*)::int AS cnt
                FROM product_item
                WHERE box_id IS NOT NULL
                GROUP BY box_id
            ) src
            WHERE b.id = src.box_id
            """
        )
    )
    op.alter_column("box", "quantity", server_default=None)

    op.create_table(
        "product_item_pour",
        sa.Column("product_item_id", sa.Integer(), sa.ForeignKey("product_item.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("glasses_total", sa.Integer(), nullable=False),
        sa.Column("glasses_sold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("glasses_total > 0", name="ck_product_item_pour_total_positive"),
        sa.CheckConstraint("glasses_sold >= 0", name="ck_product_item_pour_sold_non_negative"),
        sa.CheckConstraint("glasses_sold <= glasses_total", name="ck_product_item_pour_sold_le_total"),
        comment="Per-item pour progress for glass sales",
    )

    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_set_updated_at_product_item_pour ON product_item_pour"))
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_set_updated_at_product_item_pour
            BEFORE UPDATE ON product_item_pour
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )
    )


def downgrade() -> None:
    op.drop_table("product_item_pour")
    op.drop_column("box", "quantity")
