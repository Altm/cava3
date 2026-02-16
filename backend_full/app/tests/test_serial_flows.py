from decimal import Decimal
import pytest
from fastapi import HTTPException

from app.models.models import (
    Unit,
    ProductType,
    Product,
    ProductUnit,
    Location,
    Receipt,
    ProductItem,
    Stock,
    Box,
)
from app.services.serial_receipts import ReceiptService
from app.services.serial_boxes import BoxService
from app.services.serial_transfers import TransferService
from app.services.serial_inventories import InventoryService
from app.api.v1.routes.transfers_serial import list_transfer_items
from app.api.v1.routes.scan import get_product_item_history


def _seed_serial_product(db_session):
    base_unit = Unit(code="bottle", description="Bottle", unit_type="base", is_discrete=True)
    db_session.add(base_unit)
    pt = ProductType(name="wine", description="Wine", is_composite=False)
    db_session.add(pt)
    db_session.flush()
    product = Product(
        name="Test Wine",
        sku="SKU-1",
        primary_category="wine",
        product_type_id=pt.id,
        base_unit_id=base_unit.id,
        is_active=True,
    )
    db_session.add(product)
    db_session.flush()
    db_session.add(ProductUnit(product_id=product.id, unit_id=base_unit.id, ratio_to_base=Decimal("1.0")))
    db_session.flush()
    return product, base_unit


def _seed_locations(db_session):
    wh = Location(name="Warehouse", code="warehouse", is_active=True)
    bar = Location(name="Bar", code="bar", is_active=True)
    db_session.add_all([wh, bar])
    db_session.flush()
    return wh, bar


def test_receipt_generate_post_void(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("3"), unit_id=base_unit.id)
    with pytest.raises(HTTPException) as exc:
        rs.list_item_labels(receipt.id)
    assert exc.value.status_code == 409

    gen = rs.generate(receipt.id)
    assert gen.items_created == 3

    items = db_session.query(ProductItem).all()
    assert len(items) == 3
    assert {i.status for i in items} == {"receiving"}
    # legacy/backfill safety: if qr_code is missing, list_item_labels must rebuild from uuid
    items[0].qr_code = ""
    labels = rs.list_item_labels(receipt.id)
    assert len(labels) == 3
    assert all(label.startswith("ITM:") for label in labels)

    post_res = rs.post(receipt.id)
    assert post_res["posted_items"] == 3
    assert {i.status for i in db_session.query(ProductItem).all()} == {"in_stock"}

    stock = db_session.query(Stock).filter_by(location_id=wh.id, product_id=product.id).first()
    assert stock is not None
    assert Decimal(stock.quantity) == Decimal("3")

    void_res = rs.void(receipt.id)
    assert void_res["voided_items"] == 3
    assert {i.status for i in db_session.query(ProductItem).all()} == {"voided"}
    stock = db_session.query(Stock).filter_by(location_id=wh.id, product_id=product.id).first()
    assert Decimal(stock.quantity) == Decimal("0")


def test_transfer_box_pick_receive_and_close(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("2"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    lot_id = db_session.query(ProductItem.lot_id).first()[0]

    bs = BoxService(db_session)
    box = bs.create(product_id=product.id, lot_id=lot_id, location_id=wh.id, sealed=False)
    items = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()
    for item in items:
        bs.add_item_by_qr(box.id, item.qr_code)
    bs.seal_box(box.id)
    assert db_session.query(Box).get(box.id).sealed is True

    ts = TransferService(db_session)
    doc = ts.create(from_location_id=wh.id, to_location_id=bar.id)
    plan = ts.plan_fifo(doc.id, product.id, qty_base=2)
    assert plan.planned_items == 2

    pick_res = ts.scan(doc.id, box.qr_code, mode="picking")
    assert pick_res["picked_items"] == 2

    # warehouse aggregated stock decreased on pick
    stock_wh = db_session.query(Stock).filter_by(location_id=wh.id, product_id=product.id).first()
    assert Decimal(stock_wh.quantity) == Decimal("0")

    ts.ship(doc.id)
    recv_res = ts.scan(doc.id, box.qr_code, mode="receiving")
    assert recv_res["received_items"] == 2

    stock_bar = db_session.query(Stock).filter_by(location_id=bar.id, product_id=product.id).first()
    assert Decimal(stock_bar.quantity) == Decimal("2")

    close_res = ts.close(doc.id)
    assert close_res["lost_items"] == 0


def test_transfer_close_marks_missing_as_lost(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("1"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    ts = TransferService(db_session)
    doc = ts.create(from_location_id=wh.id, to_location_id=bar.id)
    ts.plan_fifo(doc.id, product.id, qty_base=1)

    item = db_session.query(ProductItem).first()
    ts.scan(doc.id, item.qr_code, mode="picking")
    ts.ship(doc.id)

    close_res = ts.close(doc.id)
    assert close_res["lost_items"] == 1
    item = db_session.query(ProductItem).get(item.id)
    assert item.status == "lost"
    assert item.lost_reason == "lost_in_transit"


def test_inventory_close_marks_missing_as_lost_and_decrements_stock(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("3"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    inv = InventoryService(db_session)
    doc = inv.create(location_id=wh.id)
    start = inv.start(doc.id)
    assert start["expected"] == 3

    items = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()
    inv.scan(doc.id, items[0].qr_code)
    inv.scan(doc.id, items[1].qr_code)

    close = inv.close(doc.id)
    assert close["missing"] == 1

    stock = db_session.query(Stock).filter_by(location_id=wh.id, product_id=product.id).first()
    assert Decimal(stock.quantity) == Decimal("2")


def test_transfer_items_view_marks_lost_rows(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("1"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    ts = TransferService(db_session)
    doc = ts.create(from_location_id=wh.id, to_location_id=bar.id)
    ts.plan_fifo(doc.id, product.id, qty_base=1)
    item = db_session.query(ProductItem).first()
    ts.scan(doc.id, item.qr_code, mode="picking")
    ts.ship(doc.id)
    ts.close(doc.id)

    rows = list_transfer_items(doc.id, user=None, db=db_session)
    assert len(rows) == 1
    assert rows[0].transfer_status == "closed"
    assert rows[0].is_lost is True


def test_product_item_history_contains_transfer_and_summary(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("1"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    ts = TransferService(db_session)
    doc = ts.create(from_location_id=wh.id, to_location_id=bar.id)
    ts.plan_fifo(doc.id, product.id, qty_base=1)
    item = db_session.query(ProductItem).first()
    ts.scan(doc.id, item.qr_code, mode="picking")
    ts.ship(doc.id)

    history = get_product_item_history(item.id, user=None, db=db_session)
    assert history.summary.product_item_id == item.id
    assert history.summary.product_id == product.id
    assert history.transfers
    assert history.transfers[0].transfer_doc_id == doc.id
