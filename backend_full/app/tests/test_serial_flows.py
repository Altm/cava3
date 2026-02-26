from datetime import datetime
from decimal import Decimal
import pytest
from fastapi import HTTPException

from app.models.models import (
    Ingredient,
    IngredientProductBinding,
    Unit,
    ProductType,
    Product,
    ProductUnit,
    ProductTypeUnit,
    ProductRecipe,
    ProductRecipeComponent,
    Location,
    Receipt,
    ProductItem,
    ProductItemPour,
    Stock,
    Box,
    Terminal,
    SaleEvent,
    SaleLine,
)
from app.services.serial_receipts import ReceiptService
from app.services.serial_boxes import BoxService
from app.services.serial_transfers import TransferService
from app.services.serial_inventories import InventoryService
from app.application.simple_catalog.sales import SaleCheckoutCommand, SalesCheckoutHandler
from app.application.serial.inventories import (
    GetInventoryExpectedHandler,
    GetInventoryExpectedQuery,
    GetInventoryResultHandler,
    GetInventoryResultQuery,
)
from app.infrastructure.db.uow import BoundSessionUnitOfWork
from app.schemas import simple as simple_schemas
from app.api.v1.routes.transfers_serial import list_transfer_items
from app.api.v1.routes.scan import get_product_item_history
from app.api.v1.routes.receipts import get_receipt_items


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
    assert db_session.get(Box, box.id).sealed is True

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
    item = db_session.get(ProductItem, item.id)
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


def test_inventory_expected_list_groups_boxes_and_single_items(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("4"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    items = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()
    bs = BoxService(db_session)

    closed_box = bs.create(product_id=product.id, lot_id=items[0].lot_id, location_id=wh.id, sealed=False)
    bs.add_item_by_qr(closed_box.id, items[0].qr_code)
    bs.add_item_by_qr(closed_box.id, items[1].qr_code)
    bs.seal_box(closed_box.id)

    open_box = bs.create(product_id=product.id, lot_id=items[0].lot_id, location_id=wh.id, sealed=False)
    bs.add_item_by_qr(open_box.id, items[2].qr_code)

    inv = InventoryService(db_session)
    doc = inv.create(location_id=wh.id)

    with BoundSessionUnitOfWork(db_session) as uow:
        payload = GetInventoryExpectedHandler().handle(GetInventoryExpectedQuery(inventory_doc_id=doc.id), uow)

    assert payload.status == "draft"
    assert payload.remaining_expected_count == 4
    assert len(payload.boxes) == 2
    assert len(payload.single_items) == 1
    assert payload.single_items[0].product_item_id == items[3].id

    closed_rows = [row for row in payload.boxes if row.sealed]
    assert closed_rows
    assert closed_rows[0].items_remaining == 2
    assert closed_rows[0].items == []

    open_rows = [row for row in payload.boxes if not row.sealed]
    assert open_rows
    assert open_rows[0].items_remaining == 1
    assert len(open_rows[0].items) == 1
    assert open_rows[0].items[0].product_item_id == items[2].id


def test_inventory_expected_list_hides_scanned_items(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("3"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)
    items = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()

    bs = BoxService(db_session)
    box = bs.create(product_id=product.id, lot_id=items[0].lot_id, location_id=wh.id, sealed=False)
    bs.add_item_by_qr(box.id, items[0].qr_code)
    bs.add_item_by_qr(box.id, items[1].qr_code)
    bs.seal_box(box.id)

    inv = InventoryService(db_session)
    doc = inv.create(location_id=wh.id)
    inv.start(doc.id)
    inv.scan(doc.id, box.qr_code)

    with BoundSessionUnitOfWork(db_session) as uow:
        payload = GetInventoryExpectedHandler().handle(GetInventoryExpectedQuery(inventory_doc_id=doc.id), uow)

    assert payload.status == "counting"
    assert payload.remaining_expected_count == 1
    assert payload.boxes == []
    assert len(payload.single_items) == 1
    assert payload.single_items[0].product_item_id == items[2].id


def test_inventory_scan_open_box_marks_expected_items_scanned(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("2"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)
    items = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()

    bs = BoxService(db_session)
    box = bs.create(product_id=product.id, lot_id=items[0].lot_id, location_id=wh.id, sealed=False)
    bs.add_item_by_qr(box.id, items[0].qr_code)
    bs.add_item_by_qr(box.id, items[1].qr_code)

    inv = InventoryService(db_session)
    doc = inv.create(location_id=wh.id)
    inv.start(doc.id)

    scan_res = inv.scan(doc.id, box.qr_code)
    assert scan_res["scanned_in_box"] == 2

    with BoundSessionUnitOfWork(db_session) as uow:
        payload = GetInventoryExpectedHandler().handle(GetInventoryExpectedQuery(inventory_doc_id=doc.id), uow)

    assert payload.remaining_expected_count == 0
    assert payload.boxes == []
    assert payload.single_items == []


def test_sales_checkout_sells_fifo_items_and_reduces_stock(db_session, monkeypatch):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    product.base_cost = Decimal("15.00")
    db_session.flush()

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("3"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)
    items = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()

    terminal = Terminal(terminal_id="T-1", location_id=wh.id, secret_hash="secret", status="active")
    db_session.add(terminal)
    db_session.flush()

    def _fake_send_register_request(self, *, db, terminal, payload):
        return {"status": "ok", "received_sales_count": len(payload.get("sales", []))}

    monkeypatch.setattr(SalesCheckoutHandler, "_send_register_transactions_request", _fake_send_register_request)

    with BoundSessionUnitOfWork(db_session) as uow:
        result = SalesCheckoutHandler().handle(
            SaleCheckoutCommand(
                payload=simple_schemas.SaleCheckoutRequest(
                    lines=[
                        simple_schemas.SaleCheckoutLineIn(
                            kind="product",
                            product_id=product.id,
                            quantity=Decimal("2"),
                            unit_id=base_unit.id,
                        )
                    ]
                ),
                user_id=77,
            ),
            uow,
        )

    assert result.lines
    assert result.lines[0].resolved_item_ids == [items[0].id, items[1].id]
    assert result.lines[0].quantity == Decimal("2")
    assert result.register_response["status"] == "ok"

    updated = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()
    assert updated[0].status == "sold"
    assert updated[1].status == "sold"
    assert updated[2].status == "in_stock"

    stock = db_session.query(Stock).filter_by(location_id=wh.id, product_id=product.id).first()
    assert stock is not None
    assert Decimal(stock.quantity) == Decimal("1")


def test_sales_checkout_product_line_with_portion_unit_uses_glass_flow(db_session, monkeypatch):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    glass_unit = Unit(code="glass", description="Glass", unit_type="portion", is_discrete=True)
    db_session.add(glass_unit)
    db_session.flush()
    db_session.add(ProductUnit(product_id=product.id, unit_id=glass_unit.id, ratio_to_base=Decimal("0.2")))
    db_session.flush()

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("1"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    terminal = Terminal(terminal_id="T-1", location_id=wh.id, secret_hash="secret", status="active")
    db_session.add(terminal)
    db_session.flush()

    def _fake_send_register_request(self, *, db, terminal, payload):
        return {"status": "ok", "received_sales_count": len(payload.get("sales", []))}

    monkeypatch.setattr(SalesCheckoutHandler, "_send_register_transactions_request", _fake_send_register_request)

    with BoundSessionUnitOfWork(db_session) as uow:
        result = SalesCheckoutHandler().handle(
            SaleCheckoutCommand(
                payload=simple_schemas.SaleCheckoutRequest(
                    lines=[
                        simple_schemas.SaleCheckoutLineIn(
                            kind="product",
                            product_id=product.id,
                            quantity=Decimal("1"),
                            unit_id=glass_unit.id,
                        )
                    ]
                ),
                user_id=42,
            ),
            uow,
        )

    assert result.lines
    assert result.lines[0].kind == "product"
    assert result.lines[0].quantity == Decimal("1")
    assert result.lines[0].unit_id == glass_unit.id
    assert len(result.lines[0].resolved_item_ids) == 1

    item = db_session.query(ProductItem).first()
    assert item is not None
    assert item.status == "in_stock"

    pour = db_session.query(ProductItemPour).filter_by(product_item_id=item.id).first()
    assert pour is not None
    assert pour.glasses_total == 5
    assert pour.glasses_sold == 1

    stock = db_session.query(Stock).filter_by(location_id=wh.id, product_id=product.id).first()
    assert stock is not None
    assert Decimal(str(stock.quantity)) == Decimal("0.8")


def test_sales_checkout_product_line_with_tenth_portion_uses_fractional_item_consumption(db_session, monkeypatch):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    slice_unit = Unit(code="slice", description="Slice", unit_type="portion", is_discrete=True)
    db_session.add(slice_unit)
    db_session.flush()
    db_session.add(ProductUnit(product_id=product.id, unit_id=slice_unit.id, ratio_to_base=Decimal("0.1")))
    db_session.flush()

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("1"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    terminal = Terminal(terminal_id="T-1", location_id=wh.id, secret_hash="secret", status="active")
    db_session.add(terminal)
    db_session.flush()

    def _fake_send_register_request(self, *, db, terminal, payload):
        return {"status": "ok", "received_sales_count": len(payload.get("sales", []))}

    monkeypatch.setattr(SalesCheckoutHandler, "_send_register_transactions_request", _fake_send_register_request)

    with BoundSessionUnitOfWork(db_session) as uow:
        result = SalesCheckoutHandler().handle(
            SaleCheckoutCommand(
                payload=simple_schemas.SaleCheckoutRequest(
                    lines=[
                        simple_schemas.SaleCheckoutLineIn(
                            kind="product",
                            product_id=product.id,
                            quantity=Decimal("1"),
                            unit_id=slice_unit.id,
                        )
                    ]
                ),
                user_id=43,
            ),
            uow,
        )

    assert result.lines
    assert result.lines[0].kind == "product"
    assert result.lines[0].quantity == Decimal("1")
    assert result.lines[0].unit_id == slice_unit.id
    assert len(result.lines[0].resolved_item_ids) == 1

    item = db_session.query(ProductItem).first()
    assert item is not None
    pour = db_session.query(ProductItemPour).filter_by(product_item_id=item.id).first()
    assert pour is not None
    assert pour.glasses_total == 10
    assert pour.glasses_sold == 1

    stock = db_session.query(Stock).filter_by(location_id=wh.id, product_id=product.id).first()
    assert stock is not None
    assert Decimal(str(stock.quantity)) == Decimal("0.9")


def test_sales_checkout_composite_product_consumes_component_item_fractions(db_session, monkeypatch):
    bottle = Unit(code="bottle", description="Bottle", unit_type="base", is_discrete=True)
    portion = Unit(code="glass", description="Glass", unit_type="portion", is_discrete=True)
    plate = Unit(code="plate", description="Plate", unit_type="base", is_discrete=True)
    db_session.add_all([bottle, portion, plate])
    db_session.flush()

    simple_type = ProductType(name="ingredient", description="Ingredient", is_composite=False)
    composite_type = ProductType(name="dish", description="Dish", is_composite=True)
    db_session.add_all([simple_type, composite_type])
    db_session.flush()

    c1 = Product(
        name="Comp-1",
        sku="COMP-1",
        primary_category="ingredient",
        product_type_id=simple_type.id,
        base_unit_id=bottle.id,
        base_cost=Decimal("10.00"),
        is_active=True,
    )
    c2 = Product(
        name="Comp-2",
        sku="COMP-2",
        primary_category="ingredient",
        product_type_id=simple_type.id,
        base_unit_id=bottle.id,
        base_cost=Decimal("10.00"),
        is_active=True,
    )
    c3 = Product(
        name="Comp-3",
        sku="COMP-3",
        primary_category="ingredient",
        product_type_id=simple_type.id,
        base_unit_id=bottle.id,
        base_cost=Decimal("10.00"),
        is_active=True,
    )
    dish = Product(
        name="Sandwich",
        sku="SANDWICH-1",
        primary_category="dish",
        product_type_id=composite_type.id,
        base_unit_id=plate.id,
        base_cost=Decimal("30.00"),
        is_active=True,
    )
    db_session.add_all([c1, c2, c3, dish])
    db_session.flush()

    db_session.add_all(
        [
            ProductUnit(product_id=c1.id, unit_id=bottle.id, ratio_to_base=Decimal("1.0")),
            ProductUnit(product_id=c1.id, unit_id=portion.id, ratio_to_base=Decimal("0.2")),
            ProductUnit(product_id=c2.id, unit_id=bottle.id, ratio_to_base=Decimal("1.0")),
            ProductUnit(product_id=c2.id, unit_id=portion.id, ratio_to_base=Decimal("0.2")),
            ProductUnit(product_id=c3.id, unit_id=bottle.id, ratio_to_base=Decimal("1.0")),
            ProductUnit(product_id=c3.id, unit_id=portion.id, ratio_to_base=Decimal("0.2")),
            ProductUnit(product_id=dish.id, unit_id=plate.id, ratio_to_base=Decimal("1.0")),
        ]
    )
    db_session.flush()

    ing1 = Ingredient(code="serial_ing_c1", name="Serial ingredient 1", base_unit_id=bottle.id, is_active=True)
    ing2 = Ingredient(code="serial_ing_c2", name="Serial ingredient 2", base_unit_id=bottle.id, is_active=True)
    ing3 = Ingredient(code="serial_ing_c3", name="Serial ingredient 3", base_unit_id=bottle.id, is_active=True)
    db_session.add_all([ing1, ing2, ing3])
    db_session.flush()
    db_session.add_all(
        [
            IngredientProductBinding(
                ingredient_id=ing1.id,
                product_id=c1.id,
                ratio_to_ingredient_base=Decimal("1"),
                priority=100,
                is_active=True,
            ),
            IngredientProductBinding(
                ingredient_id=ing2.id,
                product_id=c2.id,
                ratio_to_ingredient_base=Decimal("1"),
                priority=100,
                is_active=True,
            ),
            IngredientProductBinding(
                ingredient_id=ing3.id,
                product_id=c3.id,
                ratio_to_ingredient_base=Decimal("1"),
                priority=100,
                is_active=True,
            ),
        ]
    )
    recipe = ProductRecipe(
        product_id=dish.id,
        version=1,
        is_active=True,
        valid_from=datetime.utcnow(),
        valid_to=None,
    )
    db_session.add(recipe)
    db_session.flush()
    db_session.add_all(
        [
            ProductRecipeComponent(
                recipe_id=recipe.id,
                ingredient_id=ing1.id,
                quantity=Decimal("0.2"),
                unit_id=bottle.id,
            ),
            ProductRecipeComponent(
                recipe_id=recipe.id,
                ingredient_id=ing2.id,
                quantity=Decimal("0.2"),
                unit_id=bottle.id,
            ),
            ProductRecipeComponent(
                recipe_id=recipe.id,
                ingredient_id=ing3.id,
                quantity=Decimal("0.2"),
                unit_id=bottle.id,
            ),
        ]
    )
    db_session.flush()

    wh, _bar = _seed_locations(db_session)
    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, c1.id, qty=Decimal("1"), unit_id=bottle.id)
    rs.add_line(receipt.id, c2.id, qty=Decimal("1"), unit_id=bottle.id)
    rs.add_line(receipt.id, c3.id, qty=Decimal("1"), unit_id=bottle.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    terminal = Terminal(terminal_id="T-1", location_id=wh.id, secret_hash="secret", status="active")
    db_session.add(terminal)
    db_session.flush()

    def _fake_send_register_request(self, *, db, terminal, payload):
        return {"status": "ok", "received_sales_count": len(payload.get("sales", []))}

    monkeypatch.setattr(SalesCheckoutHandler, "_send_register_transactions_request", _fake_send_register_request)

    with BoundSessionUnitOfWork(db_session) as uow:
        result = SalesCheckoutHandler().handle(
            SaleCheckoutCommand(
                payload=simple_schemas.SaleCheckoutRequest(
                    lines=[
                        simple_schemas.SaleCheckoutLineIn(
                            kind="product",
                            product_id=dish.id,
                            quantity=Decimal("1"),
                            unit_id=plate.id,
                        )
                    ]
                ),
                user_id=55,
            ),
            uow,
        )

    assert result.lines
    assert result.lines[0].product_id == dish.id
    assert result.lines[0].quantity == Decimal("1")
    assert len(result.lines[0].resolved_item_ids) == 3

    component_items = (
        db_session.query(ProductItem)
        .filter(ProductItem.product_id.in_([c1.id, c2.id, c3.id]))
        .order_by(ProductItem.product_id.asc())
        .all()
    )
    assert len(component_items) == 3
    for item in component_items:
        assert item.status == "in_stock"
        pour = db_session.query(ProductItemPour).filter_by(product_item_id=item.id).first()
        assert pour is not None
        assert pour.glasses_total == 5
        assert pour.glasses_sold == 1

    for component_product in (c1, c2, c3):
        stock = db_session.query(Stock).filter_by(location_id=wh.id, product_id=component_product.id).first()
        assert stock is not None
        assert Decimal(str(stock.quantity)) == Decimal("0.8")

    composite_stock = db_session.query(Stock).filter_by(location_id=wh.id, product_id=dish.id).first()
    assert composite_stock is None


def test_sales_checkout_composite_uses_type_unit_conversion_for_components(db_session, monkeypatch):
    bottle = Unit(code="bottle", description="Bottle", unit_type="base", is_discrete=True)
    glass = Unit(code="glass", description="Glass", unit_type="portion", is_discrete=True)
    plate = Unit(code="plate", description="Plate", unit_type="base", is_discrete=True)
    db_session.add_all([bottle, glass, plate])
    db_session.flush()

    ingredient_type = ProductType(name="ingredient-type", description="Ingredient", is_composite=False)
    dish_type = ProductType(name="dish-type", description="Dish", is_composite=True)
    db_session.add_all([ingredient_type, dish_type])
    db_session.flush()

    db_session.add(
        ProductTypeUnit(product_type_id=ingredient_type.id, unit_id=glass.id, ratio_to_base=Decimal("0.2"))
    )
    db_session.flush()

    component = Product(
        name="Type-unit ingredient",
        sku="TYPE-ING-1",
        primary_category="ingredient",
        product_type_id=ingredient_type.id,
        base_unit_id=bottle.id,
        base_cost=Decimal("8.00"),
        is_active=True,
    )
    dish = Product(
        name="Type-unit dish",
        sku="TYPE-DISH-1",
        primary_category="dish",
        product_type_id=dish_type.id,
        base_unit_id=plate.id,
        base_cost=Decimal("20.00"),
        is_active=True,
    )
    db_session.add_all([component, dish])
    db_session.flush()
    db_session.add_all(
        [
            ProductUnit(product_id=component.id, unit_id=bottle.id, ratio_to_base=Decimal("1.0")),
            ProductUnit(product_id=dish.id, unit_id=plate.id, ratio_to_base=Decimal("1.0")),
        ]
    )
    ingredient = Ingredient(code="serial_ing_type", name="Type ingredient", base_unit_id=glass.id, is_active=True)
    db_session.add(ingredient)
    db_session.flush()
    db_session.add(
        IngredientProductBinding(
            ingredient_id=ingredient.id,
            product_id=component.id,
            ratio_to_ingredient_base=Decimal("5"),
            priority=100,
            is_active=True,
        )
    )
    recipe = ProductRecipe(
        product_id=dish.id,
        version=1,
        is_active=True,
        valid_from=datetime.utcnow(),
        valid_to=None,
    )
    db_session.add(recipe)
    db_session.flush()
    db_session.add(
        ProductRecipeComponent(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=Decimal("1"),
            unit_id=glass.id,
        )
    )
    db_session.flush()

    wh, _bar = _seed_locations(db_session)
    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, component.id, qty=Decimal("1"), unit_id=bottle.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    terminal = Terminal(terminal_id="T-1", location_id=wh.id, secret_hash="secret", status="active")
    db_session.add(terminal)
    db_session.flush()

    def _fake_send_register_request(self, *, db, terminal, payload):
        return {"status": "ok", "received_sales_count": len(payload.get("sales", []))}

    monkeypatch.setattr(SalesCheckoutHandler, "_send_register_transactions_request", _fake_send_register_request)

    with BoundSessionUnitOfWork(db_session) as uow:
        result = SalesCheckoutHandler().handle(
            SaleCheckoutCommand(
                payload=simple_schemas.SaleCheckoutRequest(
                    lines=[
                        simple_schemas.SaleCheckoutLineIn(
                            kind="product",
                            product_id=dish.id,
                            quantity=Decimal("1"),
                            unit_id=plate.id,
                        )
                    ]
                ),
                user_id=56,
            ),
            uow,
        )

    assert result.lines
    assert result.lines[0].product_id == dish.id
    assert len(result.lines[0].resolved_item_ids) == 1

    component_item = db_session.query(ProductItem).filter(ProductItem.product_id == component.id).first()
    assert component_item is not None
    pour = db_session.query(ProductItemPour).filter_by(product_item_id=component_item.id).first()
    assert pour is not None
    assert pour.glasses_sold == 1


def test_inventory_close_write_off_sets_lost_metadata(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("2"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    inv = InventoryService(db_session)
    doc = inv.create(location_id=wh.id)
    inv.start(doc.id)
    close_res = inv.close(doc.id)
    assert close_res["missing"] == 2

    items = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()
    assert {row.status for row in items} == {"lost"}
    assert {row.lost_reason for row in items} == {"missing_inventory"}
    assert {row.lost_doc_type for row in items} == {"inventory"}
    assert {row.lost_doc_id for row in items} == {doc.id}

    stock = db_session.query(Stock).filter_by(location_id=wh.id, product_id=product.id).first()
    assert stock is not None
    assert Decimal(stock.quantity) == Decimal("0")


def test_inventory_result_closed_contains_accounted_and_unaccounted_lists(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("2"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)
    items = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()

    bs = BoxService(db_session)
    box = bs.create(product_id=product.id, lot_id=items[0].lot_id, location_id=wh.id, sealed=False)
    bs.add_item_by_qr(box.id, items[0].qr_code)
    bs.add_item_by_qr(box.id, items[1].qr_code)
    bs.seal_box(box.id)

    inv = InventoryService(db_session)
    doc = inv.create(location_id=wh.id)
    inv.start(doc.id)
    inv.scan(doc.id, items[0].qr_code)
    inv.close(doc.id)

    with BoundSessionUnitOfWork(db_session) as uow:
        result = GetInventoryResultHandler().handle(GetInventoryResultQuery(inventory_doc_id=doc.id), uow)

    assert result.inventory_doc_id == doc.id
    assert len(result.accounted_items) == 1
    assert len(result.unaccounted_items) == 1
    assert result.accounted_items[0].product_item_qr_code == items[0].qr_code
    assert result.unaccounted_items[0].product_item_qr_code == items[1].qr_code
    assert len(result.unaccounted_boxes) == 1
    assert result.unaccounted_boxes[0].box_qr_code == box.qr_code
    assert result.unaccounted_boxes[0].status == "partial"
    assert result.unaccounted_boxes[0].counted_items == 1
    assert result.unaccounted_boxes[0].missing_items == 1


def test_inventory_scan_box_repairs_stale_box_location(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("1"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)
    item = db_session.query(ProductItem).first()

    bs = BoxService(db_session)
    box = bs.create(product_id=product.id, lot_id=item.lot_id, location_id=wh.id, sealed=False)
    bs.add_item_by_qr(box.id, item.qr_code)
    bs.seal_box(box.id)

    # simulate stale location mismatch: item already in bar, box still points to warehouse
    item.location_id = bar.id
    item.status = "in_stock"
    box.location_id = wh.id
    db_session.flush()

    inv = InventoryService(db_session)
    doc = inv.create(location_id=bar.id)
    inv.start(doc.id)
    scan_res = inv.scan(doc.id, box.qr_code)
    assert scan_res["scanned_in_box"] == 1
    assert box.location_id == bar.id


def test_transfer_receive_item_updates_box_location(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("2"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)
    items = db_session.query(ProductItem).order_by(ProductItem.id.asc()).all()

    bs = BoxService(db_session)
    box = bs.create(product_id=product.id, lot_id=items[0].lot_id, location_id=wh.id, sealed=False)
    bs.add_item_by_qr(box.id, items[0].qr_code)
    bs.add_item_by_qr(box.id, items[1].qr_code)
    bs.seal_box(box.id)

    ts = TransferService(db_session)
    doc = ts.create(from_location_id=wh.id, to_location_id=bar.id)
    ts.plan_fifo(doc.id, product.id, qty_base=2)
    ts.scan(doc.id, box.qr_code, mode="picking")
    ts.ship(doc.id)

    ts.scan(doc.id, items[0].qr_code, mode="receiving")
    assert box.location_id == bar.id

    ts.scan(doc.id, items[1].qr_code, mode="receiving")
    close_res = ts.close(doc.id)
    assert close_res["lost_items"] == 0


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
    assert any(row.event_type == "receipt" and row.doc_type == "receipt" for row in history.transfers)
    assert any(row.event_type == "transfer" and row.transfer_doc_id == doc.id for row in history.transfers)


def test_product_item_history_contains_sale_event_description(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("1"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)

    item = db_session.query(ProductItem).first()
    item.status = "sold"
    db_session.flush()

    history = get_product_item_history(item.id, user=None, db=db_session)
    sale_rows = [row for row in history.transfers if row.event_type == "sale"]
    assert sale_rows
    assert all((row.event_description or "").startswith("Продажа") for row in sale_rows)


def test_product_item_history_links_sale_event_by_resolved_item_id(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("1"), unit_id=base_unit.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)
    item = db_session.query(ProductItem).first()

    terminal = Terminal(terminal_id="TERM-1", location_id=wh.id, secret_hash="hash", status="active")
    db_session.add(terminal)
    db_session.flush()

    sale = SaleEvent(
        event_id="evt-1",
        sale_id=101,
        user_id=22,
        terminal_id=terminal.id,
        location_id=wh.id,
        status="confirmed",
        payload={
            "sale": {
                "sale_id": 101,
                "items": [
                    {
                        "product_id": product.id,
                        "quantity": 1,
                        "price": 10,
                        "resolved_item_ids": [item.id],
                    }
                ],
            }
        },
    )
    db_session.add(sale)
    db_session.flush()
    db_session.add(
        SaleLine(
            sale_event_id=sale.id,
            product_id=product.id,
            quantity=Decimal("1"),
            unit_id=base_unit.id,
            price=Decimal("10"),
            currency="USD",
        )
    )
    item.status = "sold"
    db_session.flush()

    history = get_product_item_history(item.id, user=None, db=db_session)
    assert any(row.event_type == "sale" and row.doc_id == sale.id for row in history.transfers)


def test_receipt_auto_box_supports_multiple_box_sizes(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, product.id, qty=Decimal("7"), unit_id=base_unit.id)
    rs.generate(receipt.id)

    first = rs.auto_box(receipt.id, items_per_box=3, include_partial=False, seal_full_boxes=True)
    assert first.boxes_created == 2
    assert first.items_packed == 6
    assert first.items_remaining_unboxed == 1
    assert all(box.packed_items == 3 for box in first.boxes)
    assert all(box.sealed is True for box in first.boxes)

    second = rs.auto_box(receipt.id, items_per_box=1, include_partial=True, seal_full_boxes=True)
    assert second.boxes_created == 1
    assert second.items_packed == 1
    assert second.items_remaining_unboxed == 0
    assert second.boxes[0].packed_items == 1

    assert db_session.query(Box).count() == 3


def test_receipt_items_view_returns_purchase_and_lot_data(db_session):
    product, base_unit = _seed_serial_product(db_session)
    wh, _bar = _seed_locations(db_session)

    rs = ReceiptService(db_session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(
        receipt.id,
        product.id,
        qty=Decimal("2"),
        unit_id=base_unit.id,
        supplier_lot_number="SUP-LOT-001",
    )
    rs.generate(receipt.id)

    items = get_receipt_items(receipt.id, user=None, db=db_session)
    assert len(items) == 2
    assert all(row.receipt_id == receipt.id for row in items)
    assert all(row.product_id == product.id for row in items)
    assert all(row.supplier_lot_number == "SUP-LOT-001" for row in items)
