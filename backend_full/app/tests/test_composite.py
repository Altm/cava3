from decimal import Decimal
from app.services.sales_service import SalesService
from app.models.models import (
    Unit,
    ProductType,
    Product,
    Location,
    Terminal,
    ProductComposite,
    Stock,
    ProductUnit,
)


def seed_composite(db):
    bottle = Unit(code="bottle", description="Bottle")
    glass = Unit(code="glass", description="Glass")
    wine_type = ProductType(name="wine", is_composite=False)
    snack_type = ProductType(name="snack", is_composite=True)
    loc = Location(name="Bar2", code="bar")
    db.add_all([bottle, glass, wine_type, snack_type, loc])
    db.flush()

    wine = Product(
        name="Red wine",
        sku="WINE01",
        primary_category="wine",
        product_type_id=wine_type.id,
        base_unit_id=bottle.id,
        is_active=True,
    )
    sandwich = Product(
        name="Sandwich",
        sku="SNACK01",
        primary_category="snack",
        product_type_id=snack_type.id,
        base_unit_id=glass.id,
        is_active=True,
    )
    db.add_all([wine, sandwich])
    db.flush()

    # Conversions for wine: 1 bottle = 5 glasses => 1 glass = 0.2 bottle
    db.add_all(
        [
            ProductUnit(product_id=wine.id, unit_id=bottle.id, ratio_to_base=Decimal("1.0")),
            ProductUnit(product_id=wine.id, unit_id=glass.id, ratio_to_base=Decimal("0.2")),
        ]
    )

    comp = ProductComposite(
        parent_product_id=sandwich.id,
        component_product_id=wine.id,
        quantity=Decimal("1"),
        unit_id=glass.id,
    )
    db.add(comp)

    term = Terminal(terminal_id="t2", location_id=loc.id, secret_hash="secret")
    db.add(term)
    stock = Stock(location_id=loc.id, product_id=wine.id, quantity=Decimal("5"), unit_id=bottle.id)
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
