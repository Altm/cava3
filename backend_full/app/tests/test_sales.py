from decimal import Decimal
import pytest
from app.services.sales_service import SalesService
from app.services.stock_service import StockService
from app.common.errors import IdempotencyError, ValidationError
from app.models.models import (
    Unit,
    UnitConversion,
    ProductType,
    Product,
    Location,
    Terminal,
    Stock,
)


def seed_core(db):
    bottle = Unit(code="bottle", description="Bottle")
    glass = Unit(code="glass", description="Glass")
    conv = UnitConversion(from_unit="glass", to_unit="bottle", ratio=Decimal("0.2"))
    wine_type = ProductType(name="wine")
    wine = Product(
        name="Red wine",
        sku="WINE01",
        primary_category="wine",
        product_type_id=1,
        base_unit_code="bottle",
        is_composite=False,
    )
    loc = Location(name="Bar", kind="bar")
    term = Terminal(terminal_id="t1", location_id=1, secret_hash="secret")
    db.add_all([bottle, glass, conv, wine_type, wine, loc, term])
    db.flush()
    stock = Stock(location_id=loc.id, product_id=wine.id, quantity=Decimal("10"), unit_code="bottle")
    db.add(stock)
    db.commit()
    return wine, loc, term


def test_ingest_idempotent(db_session):
    wine, loc, term = seed_core(db_session)
    service = SalesService(db_session)
    service.ingest_sale("e1", term.id, loc.id, [{"product_id": wine.id, "quantity": 1, "unit": "bottle", "price": 10}])
    with pytest.raises(IdempotencyError):
        service.ingest_sale("e1", term.id, loc.id, [{"product_id": wine.id, "quantity": 1, "unit": "bottle", "price": 10}])


def test_daily_reconcile_deducts_fraction(db_session):
    wine, loc, term = seed_core(db_session)
    service = SalesService(db_session)
    result = service.reconcile_daily(
        term.id,
        loc.id,
        [
            {
                "event_id": "d1",
                "lines": [
                    {"product_id": wine.id, "quantity": Decimal("5"), "unit": "glass", "price": 5},
                ],
            }
        ],
    )
    db_session.commit()
    stock = db_session.query(Stock).first()
    assert float(stock.quantity) == 9.0
    assert "d1" in result["confirmed_events"]


def test_stock_cannot_go_negative(db_session):
    wine, loc, term = seed_core(db_session)
    stock_service = StockService(db_session)
    with pytest.raises(ValidationError):
        stock_service.adjust_stock(loc.id, wine.id, Decimal("-100"), "bottle")
