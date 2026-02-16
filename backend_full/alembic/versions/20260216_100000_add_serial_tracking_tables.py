"""add serial tracking tables (receipts, lots, items, boxes, transfers, inventories)

Revision ID: 20260216_100000
Revises: 20260216_090000
Create Date: 2026-02-16 10:00:00.000000

Implements serial inventory tracking by unit (product_item) and packaging (box)
with operational documents for receipt, transfer and inventory counting.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260216_100000"
down_revision = "20260216_090000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "receipt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("to_location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=False, comment="Warehouse location"),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="draft",
            comment="draft|generated|posted|void",
        ),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True, comment="Creator user"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        comment="Receipt document (incoming goods to warehouse)",
    )

    op.create_table(
        "receipt_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("receipt_id", sa.Integer(), sa.ForeignKey("receipt.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("qty", sa.Numeric(18, 6), nullable=False, comment="Input quantity"),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("unit.id"), nullable=False, comment="Input unit"),
        sa.Column("supplier_lot_number", sa.String(100), nullable=True, comment="Optional supplier lot reference"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        comment="Receipt document line",
    )
    op.create_index("ix_receipt_line_receipt_id", "receipt_line", ["receipt_id"])

    op.create_table(
        "stock_lot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("receipt_id", sa.Integer(), sa.ForeignKey("receipt.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("supplier_lot_number", sa.String(100), nullable=True, comment="Optional supplier lot reference"),
        sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Lot received timestamp (FIFO)"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        comment="Stock lot created during receipt generation",
    )
    op.create_index("ix_stock_lot_product_id", "stock_lot", ["product_id"])
    op.create_index("ix_stock_lot_receipt_id", "stock_lot", ["receipt_id"])

    op.create_table(
        "transfer_doc",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=False),
        sa.Column("to_location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=False),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="draft",
            comment="draft|picking|shipped|closed|canceled",
        ),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True, comment="Creator user"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        comment="Transfer document (warehouse -> bar)",
    )

    op.create_table(
        "transfer_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transfer_doc_id", sa.Integer(), sa.ForeignKey("transfer_doc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("qty_base", sa.Integer(), nullable=False, comment="Planned quantity in product base discrete units"),
        sa.Column("pick_policy", sa.String(16), nullable=False, server_default="fifo", comment="Picking policy (fifo)"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        comment="Transfer document line",
    )
    op.create_index("ix_transfer_line_doc", "transfer_line", ["transfer_doc_id"])

    op.create_table(
        "box",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uuid", sa.Uuid(), nullable=False, unique=True, comment="Technical UUID used for QR"),
        sa.Column("qr_code", sa.Text(), nullable=False, unique=True, comment="BOX:{uuid}"),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("stock_lot.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=False),
        sa.Column("sealed", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="true=closed box, false=open box"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active", comment="active|voided"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        comment="Physical box for a single product and lot",
    )
    op.create_index("ix_box_loc_product_lot", "box", ["location_id", "product_id", "lot_id"])
    op.create_index("ix_box_sealed", "box", ["sealed"])

    op.create_table(
        "product_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uuid", sa.Uuid(), nullable=False, unique=True, comment="Technical UUID used for QR"),
        sa.Column("qr_code", sa.Text(), nullable=False, unique=True, comment="ITM:{uuid}"),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("stock_lot.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=False),
        sa.Column("box_id", sa.Integer(), sa.ForeignKey("box.id"), nullable=True, comment="Current box membership (1->N)"),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="receiving",
            comment="receiving|in_stock|in_transit|sold|damaged|lost|voided",
        ),
        sa.Column("reserved_transfer_doc_id", sa.Integer(), sa.ForeignKey("transfer_doc.id"), nullable=True, comment="Reservation lock for transfer planning"),
        sa.Column("reserved_at", sa.DateTime(), nullable=True, comment="Reservation timestamp"),
        sa.Column("lost_reason", sa.String(32), nullable=True, comment="lost_in_transit|missing_inventory|damaged"),
        sa.Column("lost_doc_type", sa.String(16), nullable=True, comment="transfer|inventory"),
        sa.Column("lost_doc_id", sa.Integer(), nullable=True, comment="Document id for loss event"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        comment="Serialized unit (bottle) with QR code",
    )
    op.create_index("ix_product_item_loc_prod_status", "product_item", ["location_id", "product_id", "status"])
    op.create_index("ix_product_item_lot", "product_item", ["lot_id"])
    op.create_index("ix_product_item_reserved_doc", "product_item", ["reserved_transfer_doc_id"])
    op.create_index("ix_product_item_box_id", "product_item", ["box_id"])

    op.create_table(
        "transfer_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transfer_line_id", sa.Integer(), sa.ForeignKey("transfer_line.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_item_id", sa.Integer(), sa.ForeignKey("product_item.id"), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="planned", comment="planned|picked|removed"),
        sa.Column("reserved_at", sa.DateTime(), nullable=True),
        sa.Column("picked_at", sa.DateTime(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        sa.UniqueConstraint("transfer_line_id", "product_item_id", name="uq_transfer_item_line_item"),
        comment="Transfer line to serialized items mapping",
    )
    op.create_index("ix_transfer_item_line", "transfer_item", ["transfer_line_id"])
    op.create_index("ix_transfer_item_item", "transfer_item", ["product_item_id"])

    op.create_table(
        "inventory_doc",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft", comment="draft|counting|closed|void"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True, comment="Creator user"),
        sa.Column("closed_at", sa.DateTime(), nullable=True, comment="Close timestamp"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        comment="Inventory counting document for a location",
    )

    op.create_table(
        "inventory_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inventory_doc_id", sa.Integer(), sa.ForeignKey("inventory_doc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_item_id", sa.Integer(), sa.ForeignKey("product_item.id"), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="expected", comment="expected|scanned|missing|unexpected"),
        sa.Column("scanned_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row creation timestamp"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Row update timestamp"),
        sa.UniqueConstraint("inventory_doc_id", "product_item_id", name="uq_inventory_item_doc_item"),
        comment="Inventory doc to serialized items mapping",
    )
    op.create_index("ix_inventory_item_doc", "inventory_item", ["inventory_doc_id"])
    op.create_index("ix_inventory_item_item", "inventory_item", ["product_item_id"])

    # updated_at triggers (function is created in previous migration)
    for table in [
        "receipt",
        "receipt_line",
        "stock_lot",
        "box",
        "product_item",
        "transfer_doc",
        "transfer_line",
        "transfer_item",
        "inventory_doc",
        "inventory_item",
    ]:
        trigger_name = f"trg_set_updated_at_{table}"
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table}"))
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER {trigger_name}
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION set_updated_at();
                """
            )
        )


def downgrade() -> None:
    # Drop new tables (cascade)
    for table in [
        "inventory_item",
        "inventory_doc",
        "transfer_item",
        "product_item",
        "box",
        "transfer_line",
        "transfer_doc",
        "stock_lot",
        "receipt_line",
        "receipt",
    ]:
        op.drop_table(table)

