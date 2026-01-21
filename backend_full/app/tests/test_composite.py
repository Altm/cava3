from decimal import Decimal
from app.services.sales_service import SalesService
from app.models.models import (
    Unit,
    UnitConversion,
    ProductType,
    Product,
    Location,
    Terminal,
    CompositeComponent,
    Stock,
)


def seed_composite(db):
    bottle = Unit(code="bottle", description="Bottle")
    glass = Unit(code="glass", description="Glass")
    conv = UnitConversion(from_unit="glass", to_unit="bottle", ratio=Decimal("0.2"))
    wine_type = ProductType(name="wine")
    snack_type = ProductType(name="snack")
    wine = Product(
        name="Red wine",
        sku="WINE01",
        primary_category="wine",
        product_type_id=1,
        base_unit_code="bottle",
        is_composite=False,
    )
    sandwich = Product(
        name="Sandwich",
        sku="SNACK01",
        primary_category="snack",
        product_type_id=2,
        base_unit_code="glass",
        is_composite=True,
    )
    db.add_all([bottle, glass, conv, wine_type, snack_type, wine, sandwich])
    db.flush()
    comp = CompositeComponent(parent_product_id=sandwich.id, component_product_id=wine.id, quantity=Decimal("1"), unit_code="glass")
    db.add(comp)
    loc = Location(name="Bar2", kind="bar")
    db.add(loc)
    db.flush()
    term = Terminal(terminal_id="t2", location_id=loc.id, secret_hash="secret")
    db.add(term)
    stock = Stock(location_id=loc.id, product_id=wine.id, quantity=Decimal("5"), unit_code="bottle")
    db.add(stock)
    db.commit()
    return sandwich, wine, loc, term


def test_composite_expansion_and_deduction(db_session):
    sandwich, wine, loc, term = seed_composite(db_session)
    service = SalesService(db_session)
    service.reconcile_daily(
        term.id,
        loc.id,
        [
            {
                "event_id": "cmp1",
                "lines": [{"product_id": sandwich.id, "quantity": 2, "unit": "glass", "price": 0}],
            }
        ],
    )
    db_session.commit()
    stock = db_session.query(Stock).filter_by(product_id=wine.id).first()
    assert float(stock.quantity) == 4.6
