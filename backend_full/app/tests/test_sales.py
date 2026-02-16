from decimal import Decimal
import pytest
from app.services.sales_service import SalesService
from app.services.stock_service import StockService
from app.common.errors import IdempotencyError
from app.models.models import (
    Unit,
    ProductType,
    Product,
    Location,
    Terminal,
    Stock,
    ProductUnit,
)
from fastapi import HTTPException


def seed_core(db):
    bottle = Unit(code="bottle", description="Bottle")
    glass = Unit(code="glass", description="Glass")
    wine_type = ProductType(name="wine", is_composite=False)
    loc = Location(name="Bar", code="bar")
    db.add_all([bottle, glass, wine_type, loc])
    db.flush()

    wine = Product(
        name="Red wine",
        sku="WINE01",
        primary_category="wine",
        product_type_id=wine_type.id,
        base_unit_id=bottle.id,
        is_active=True,
    )
    db.add(wine)
    db.flush()

    # Product-specific conversions: 1 bottle = 5 glasses => 1 glass = 0.2 bottle
    db.add_all(
        [
            ProductUnit(product_id=wine.id, unit_id=bottle.id, ratio_to_base=Decimal("1.0")),
            ProductUnit(product_id=wine.id, unit_id=glass.id, ratio_to_base=Decimal("0.2")),
        ]
    )
    term = Terminal(terminal_id="t1", location_id=loc.id, secret_hash="secret")
    stock = Stock(location_id=loc.id, product_id=wine.id, quantity=Decimal("10"), unit_id=bottle.id)
    db.add_all([term, stock])
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
    bottle = db_session.query(Unit).filter_by(code="bottle").first()
    with pytest.raises(HTTPException):
        stock_service.adjust_stock(loc.id, wine.id, Decimal("-100"), bottle.id)
