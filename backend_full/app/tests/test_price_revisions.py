from decimal import Decimal

from app.application.simple_catalog.prices import (
    CreatePriceRevisionCommand,
    CreatePriceRevisionHandler,
    GetCurrentPriceHandler,
    GetCurrentPriceQuery,
    ListPriceCalculatorsHandler,
    ListPriceCalculatorsQuery,
    ListPriceRevisionsHandler,
    ListPriceRevisionsQuery,
)
from app.infrastructure.db.uow import BoundSessionUnitOfWork
from app.models.models import Location, PriceList, Product, ProductType, ProductUnit, Stock, Unit
from app.schemas import simple as schemas


def _seed_price_context(db_session):
    unit = Unit(code="bottle", description="Bottle", unit_type="base", is_discrete=True)
    location = Location(name="Main Bar", code="bar", is_active=True)
    product_type = ProductType(name="wine", is_composite=False)
    db_session.add_all([unit, location, product_type])
    db_session.flush()

    product1 = Product(
        product_type_id=product_type.id,
        name="Wine A",
        sku="W-A",
        primary_category="wine",
        base_cost=Decimal("100.00"),
        base_unit_id=unit.id,
        is_active=True,
    )
    product2 = Product(
        product_type_id=product_type.id,
        name="Wine B",
        sku="W-B",
        primary_category="wine",
        base_cost=Decimal("200.00"),
        base_unit_id=unit.id,
        is_active=True,
    )
    db_session.add_all([product1, product2])
    db_session.flush()
    db_session.add_all(
        [
            ProductUnit(product_id=product1.id, unit_id=unit.id, ratio_to_base=Decimal("1")),
            ProductUnit(product_id=product2.id, unit_id=unit.id, ratio_to_base=Decimal("1")),
            Stock(location_id=location.id, product_id=product1.id, unit_id=unit.id, quantity=Decimal("10")),
            Stock(location_id=location.id, product_id=product2.id, unit_id=unit.id, quantity=Decimal("5")),
        ]
    )
    db_session.flush()
    return location, unit, product1, product2


def test_price_revision_percent_updates_current_and_history(db_session):
    location, unit, product1, product2 = _seed_price_context(db_session)
    db_session.add(
        PriceList(
            location_id=location.id,
            product_id=product1.id,
            unit_id=unit.id,
            currency="EUR",
            amount=Decimal("120.00"),
        )
    )
    db_session.flush()

    payload = schemas.PriceRevisionCreate(
        location_id=location.id,
        name="+5%",
        mode="percent",
        percent_delta=Decimal("5"),
    )
    with BoundSessionUnitOfWork(db_session) as uow:
        detail = CreatePriceRevisionHandler().handle(
            CreatePriceRevisionCommand(payload=payload, created_by_user_id=77),
            uow,
        )

    assert detail.mode == "percent"
    assert detail.created_by_user_id == 77
    assert len(detail.items) == 2

    amounts = {(item.product_id, item.unit_id): item.amount for item in detail.items}
    assert amounts[(product1.id, unit.id)] == Decimal("126.00")
    assert amounts[(product2.id, unit.id)] == Decimal("210.00")

    current_rows = (
        db_session.query(PriceList)
        .filter(PriceList.location_id == location.id)
        .order_by(PriceList.product_id.asc())
        .all()
    )
    assert len(current_rows) == 2
    assert Decimal(str(current_rows[0].amount)) == Decimal("126.00")
    assert Decimal(str(current_rows[1].amount)) == Decimal("210.00")

    with BoundSessionUnitOfWork(db_session) as uow:
        history = ListPriceRevisionsHandler().handle(
            ListPriceRevisionsQuery(location_id=location.id, limit=10, offset=0),
            uow,
        )
    assert len(history) == 1
    assert history[0].items_count == 2


def test_price_revision_fixed_and_current_returns_latest(db_session):
    location, unit, product1, product2 = _seed_price_context(db_session)
    db_session.add(
        PriceList(
            location_id=location.id,
            product_id=product1.id,
            unit_id=unit.id,
            currency="EUR",
            amount=Decimal("120.00"),
        )
    )
    db_session.flush()

    with BoundSessionUnitOfWork(db_session) as uow:
        first = CreatePriceRevisionHandler().handle(
            CreatePriceRevisionCommand(
                payload=schemas.PriceRevisionCreate(
                    location_id=location.id,
                    name="+5%",
                    mode="percent",
                    percent_delta=Decimal("5"),
                ),
                created_by_user_id=1,
            ),
            uow,
        )
    with BoundSessionUnitOfWork(db_session) as uow:
        second = CreatePriceRevisionHandler().handle(
            CreatePriceRevisionCommand(
                payload=schemas.PriceRevisionCreate(
                    location_id=location.id,
                    name="+10",
                    mode="fixed",
                    amount_delta=Decimal("10"),
                ),
                created_by_user_id=2,
            ),
            uow,
        )
    assert second.id > first.id

    with BoundSessionUnitOfWork(db_session) as uow:
        current = GetCurrentPriceHandler().handle(GetCurrentPriceQuery(location_id=location.id), uow)
    assert current.revision_id == second.id
    amounts = {(item.product_id, item.unit_id): item.amount for item in current.items}
    assert amounts[(product1.id, unit.id)] == Decimal("136.00")
    assert amounts[(product2.id, unit.id)] == Decimal("220.00")


def test_price_revision_calculator_mode(db_session):
    location, unit, product1, _product2 = _seed_price_context(db_session)
    db_session.add(
        PriceList(
            location_id=location.id,
            product_id=product1.id,
            unit_id=unit.id,
            currency="EUR",
            amount=Decimal("100.00"),
        )
    )
    db_session.flush()

    with BoundSessionUnitOfWork(db_session) as uow:
        detail = CreatePriceRevisionHandler().handle(
            CreatePriceRevisionCommand(
                payload=schemas.PriceRevisionCreate(
                    location_id=location.id,
                    name="calculator",
                    mode="calculator",
                    calculator_file="example_multiplier.py",
                    calculator_class="ExampleMultiplierCalculator",
                    calculator_params={"multiplier": "1.1", "offset": "2"},
                ),
                created_by_user_id=3,
            ),
            uow,
        )

    line = [item for item in detail.items if item.product_id == product1.id and item.unit_id == unit.id][0]
    assert line.amount == Decimal("112.00")


def test_price_calculators_list_contains_example(db_session):
    with BoundSessionUnitOfWork(db_session) as uow:
        rows = ListPriceCalculatorsHandler().handle(ListPriceCalculatorsQuery(), uow)

    assert any(row.file == "example_multiplier.py" and row.class_name == "ExampleMultiplierCalculator" for row in rows)


def test_price_revision_uses_only_in_stock_products(db_session):
    location, unit, _product1, _product2 = _seed_price_context(db_session)

    product_type = db_session.query(ProductType).first()
    out_of_stock = Product(
        product_type_id=product_type.id,
        name="Wine C",
        sku="W-C",
        primary_category="wine",
        base_cost=Decimal("300.00"),
        base_unit_id=unit.id,
        is_active=True,
    )
    db_session.add(out_of_stock)
    db_session.flush()
    db_session.add(ProductUnit(product_id=out_of_stock.id, unit_id=unit.id, ratio_to_base=Decimal("1")))
    db_session.flush()

    with BoundSessionUnitOfWork(db_session) as uow:
        detail = CreatePriceRevisionHandler().handle(
            CreatePriceRevisionCommand(
                payload=schemas.PriceRevisionCreate(
                    location_id=location.id,
                    name="+5%",
                    mode="percent",
                    percent_delta=Decimal("5"),
                ),
                created_by_user_id=10,
            ),
            uow,
        )

    product_ids = {item.product_id for item in detail.items}
    assert out_of_stock.id not in product_ids


def test_current_prices_without_revision_are_filtered_by_stock(db_session):
    location, unit, product1, product2 = _seed_price_context(db_session)

    # Mark second product out of stock and create raw price rows without revisions.
    stock_row = (
        db_session.query(Stock)
        .filter(Stock.location_id == location.id, Stock.product_id == product2.id)
        .first()
    )
    stock_row.quantity = Decimal("0")
    db_session.add_all(
        [
            PriceList(location_id=location.id, product_id=product1.id, unit_id=unit.id, currency="EUR", amount=Decimal("100.00")),
            PriceList(location_id=location.id, product_id=product2.id, unit_id=unit.id, currency="EUR", amount=Decimal("200.00")),
        ]
    )
    db_session.flush()

    with BoundSessionUnitOfWork(db_session) as uow:
        current = GetCurrentPriceHandler().handle(GetCurrentPriceQuery(location_id=location.id), uow)

    product_ids = {item.product_id for item in current.items}
    assert product1.id in product_ids
    assert product2.id not in product_ids
