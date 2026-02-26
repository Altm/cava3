from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from tempfile import NamedTemporaryFile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.simple_catalog.sales import SaleCheckoutCommand, SalesCheckoutHandler
from app.infrastructure.db.base import Base
from app.infrastructure.db.uow import BoundSessionUnitOfWork
from app.models.models import (
    Ingredient,
    IngredientProductBinding,
    Location,
    Product,
    ProductRecipe,
    ProductRecipeComponent,
    ProductType,
    ProductUnit,
    Terminal,
    Unit,
)
from app.schemas import simple as simple_schemas
from app.services.serial_receipts import ReceiptService


pytestmark = pytest.mark.performance


def _seed_for_load_test(session):
    bottle = Unit(code="bottle", description="Bottle", unit_type="base", is_discrete=True)
    portion = Unit(code="glass", description="Glass", unit_type="portion", is_discrete=True)
    plate = Unit(code="plate", description="Plate", unit_type="base", is_discrete=True)
    session.add_all([bottle, portion, plate])
    session.flush()

    ingredient_type = ProductType(name="perf_ing", description="Ingredient", is_composite=False)
    dish_type = ProductType(name="perf_dish", description="Dish", is_composite=True)
    session.add_all([ingredient_type, dish_type])
    session.flush()

    c1 = Product(
        name="Perf Comp 1",
        sku="PERF-C1",
        primary_category="ingredient",
        product_type_id=ingredient_type.id,
        base_unit_id=bottle.id,
        base_cost=Decimal("10.00"),
        portions_per_unit=5,
        is_active=True,
    )
    c2 = Product(
        name="Perf Comp 2",
        sku="PERF-C2",
        primary_category="ingredient",
        product_type_id=ingredient_type.id,
        base_unit_id=bottle.id,
        base_cost=Decimal("10.00"),
        portions_per_unit=5,
        is_active=True,
    )
    dish = Product(
        name="Perf Dish",
        sku="PERF-DISH",
        primary_category="dish",
        product_type_id=dish_type.id,
        base_unit_id=plate.id,
        base_cost=Decimal("25.00"),
        is_active=True,
    )
    session.add_all([c1, c2, dish])
    session.flush()

    session.add_all(
        [
            ProductUnit(product_id=c1.id, unit_id=bottle.id, ratio_to_base=Decimal("1")),
            ProductUnit(product_id=c1.id, unit_id=portion.id, ratio_to_base=Decimal("0.2")),
            ProductUnit(product_id=c2.id, unit_id=bottle.id, ratio_to_base=Decimal("1")),
            ProductUnit(product_id=c2.id, unit_id=portion.id, ratio_to_base=Decimal("0.2")),
            ProductUnit(product_id=dish.id, unit_id=plate.id, ratio_to_base=Decimal("1")),
        ]
    )
    ing1 = Ingredient(code="perf_ing_1", name="Perf Ingredient 1", base_unit_id=bottle.id, is_active=True)
    ing2 = Ingredient(code="perf_ing_2", name="Perf Ingredient 2", base_unit_id=bottle.id, is_active=True)
    session.add_all([ing1, ing2])
    session.flush()
    session.add_all(
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
        ]
    )
    recipe = ProductRecipe(
        product_id=dish.id,
        version=1,
        is_active=True,
        valid_from=datetime.utcnow(),
        valid_to=None,
    )
    session.add(recipe)
    session.flush()
    session.add_all(
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
        ]
    )
    session.flush()

    wh = Location(name="Perf Warehouse", code="warehouse", is_active=True)
    session.add(wh)
    session.flush()
    session.add(Terminal(terminal_id="T-1", location_id=wh.id, secret_hash="secret", status="active"))
    session.flush()

    rs = ReceiptService(session)
    receipt = rs.create(to_location_id=wh.id)
    rs.add_line(receipt.id, c1.id, qty=Decimal("40"), unit_id=bottle.id)
    rs.add_line(receipt.id, c2.id, qty=Decimal("40"), unit_id=bottle.id)
    rs.generate(receipt.id)
    rs.post(receipt.id)
    session.commit()
    return dish.id, plate.id


@pytest.mark.performance
def test_composite_sale_under_load():
    if os.getenv("RUN_PERFORMANCE_TESTS") != "1":
        pytest.skip("Set RUN_PERFORMANCE_TESTS=1 to execute performance tests")

    with NamedTemporaryFile(suffix=".sqlite") as db_file:
        engine = create_engine(
            f"sqlite:///{db_file.name}",
            connect_args={"check_same_thread": False, "timeout": 30},
            future=True,
        )
        SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
        Base.metadata.create_all(bind=engine)

        setup_session = SessionLocal()
        dish_id, plate_id = _seed_for_load_test(setup_session)
        setup_session.close()

        def _fake_send(self, *, db, terminal, payload):
            return {"status": "ok", "received_sales_count": len(payload.get("sales", []))}

        original_send = SalesCheckoutHandler._send_register_transactions_request
        SalesCheckoutHandler._send_register_transactions_request = _fake_send
        try:
            def make_sale(_: int) -> bool:
                session = SessionLocal()
                try:
                    with BoundSessionUnitOfWork(session) as uow:
                        SalesCheckoutHandler().handle(
                            SaleCheckoutCommand(
                                payload=simple_schemas.SaleCheckoutRequest(
                                    lines=[
                                        simple_schemas.SaleCheckoutLineIn(
                                            kind="product",
                                            product_id=dish_id,
                                            quantity=Decimal("1"),
                                            unit_id=plate_id,
                                        )
                                    ]
                                ),
                                user_id=12,
                            ),
                            uow,
                        )
                        uow.commit()
                    return True
                except Exception:
                    session.rollback()
                    return False
                finally:
                    session.close()

            with ThreadPoolExecutor(max_workers=25) as pool:
                results = list(pool.map(make_sale, range(100)))
        finally:
            SalesCheckoutHandler._send_register_transactions_request = original_send

        success_count = sum(1 for ok in results if ok)
        assert success_count >= 85
