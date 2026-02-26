from datetime import datetime
from decimal import Decimal

from app.application.simple_catalog.products import (
    GetProductRecipeHistoryHandler,
    GetProductRecipeHistoryQuery,
)
from app.infrastructure.db.uow import BoundSessionUnitOfWork
from app.models.models import (
    Ingredient,
    IngredientProductBinding,
    Product,
    ProductRecipe,
    ProductRecipeComponent,
    ProductType,
    Unit,
)


def _seed_recipe_history(db_session) -> int:
    base_unit = Unit(code="bottle_hist", description="Bottle", unit_type="base", is_discrete=True)
    portion_unit = Unit(code="ml_hist", description="Milliliter", unit_type="portion", is_discrete=False)
    db_session.add_all([base_unit, portion_unit])
    db_session.flush()

    product_type = ProductType(name="RecipeHistoryType", is_composite=True, strict_units_by_type=False)
    db_session.add(product_type)
    db_session.flush()

    parent = Product(
        name="History Product",
        sku="HISTORY-PRODUCT",
        primary_category=product_type.name,
        product_type_id=product_type.id,
        base_unit_id=base_unit.id,
        base_cost=Decimal("10.00"),
        is_active=True,
    )
    component_a = Product(
        name="Component A",
        sku="HISTORY-COMP-A",
        primary_category=product_type.name,
        product_type_id=product_type.id,
        base_unit_id=base_unit.id,
        base_cost=Decimal("3.00"),
        is_active=True,
    )
    component_b = Product(
        name="Component B",
        sku="HISTORY-COMP-B",
        primary_category=product_type.name,
        product_type_id=product_type.id,
        base_unit_id=portion_unit.id,
        base_cost=Decimal("2.00"),
        is_active=True,
    )
    db_session.add_all([parent, component_a, component_b])
    db_session.flush()

    ingredient_a = Ingredient(
        code="hist_ing_a",
        name="Ingredient A",
        base_unit_id=base_unit.id,
        is_active=True,
    )
    ingredient_b = Ingredient(
        code="hist_ing_b",
        name="Ingredient B",
        base_unit_id=portion_unit.id,
        is_active=True,
    )
    db_session.add_all([ingredient_a, ingredient_b])
    db_session.flush()
    db_session.add_all(
        [
            IngredientProductBinding(
                ingredient_id=ingredient_a.id,
                product_id=component_a.id,
                ratio_to_ingredient_base=Decimal("1"),
                priority=100,
                is_active=True,
            ),
            IngredientProductBinding(
                ingredient_id=ingredient_b.id,
                product_id=component_b.id,
                ratio_to_ingredient_base=Decimal("1"),
                priority=100,
                is_active=True,
            ),
        ]
    )
    db_session.flush()

    recipe_v1 = ProductRecipe(
        product_id=parent.id,
        version=1,
        is_active=False,
        valid_from=datetime(2026, 1, 1, 0, 0, 0),
        valid_to=datetime(2026, 2, 1, 0, 0, 0),
        created_by=7,
    )
    recipe_v2 = ProductRecipe(
        product_id=parent.id,
        version=2,
        is_active=True,
        valid_from=datetime(2026, 2, 1, 0, 0, 0),
        valid_to=None,
        created_by=9,
    )
    db_session.add_all([recipe_v1, recipe_v2])
    db_session.flush()

    db_session.add_all(
        [
            ProductRecipeComponent(
                recipe_id=recipe_v1.id,
                ingredient_id=ingredient_a.id,
                quantity=Decimal("0.100000"),
                unit_id=base_unit.id,
            ),
            ProductRecipeComponent(
                recipe_id=recipe_v2.id,
                ingredient_id=ingredient_b.id,
                quantity=Decimal("20.000000"),
                unit_id=portion_unit.id,
                waste_factor=Decimal("0.0500"),
            ),
        ]
    )
    db_session.flush()
    return parent.id


def test_recipe_history_returns_versions_desc(db_session):
    product_id = _seed_recipe_history(db_session)

    with BoundSessionUnitOfWork(db_session) as uow:
        result = GetProductRecipeHistoryHandler().handle(
            GetProductRecipeHistoryQuery(
                product_id=product_id,
                active_at=None,
                date_from=None,
                date_to=None,
            ),
            uow,
        )

    assert result.product_id == product_id
    assert len(result.versions) == 2
    assert [row.version for row in result.versions] == [2, 1]
    assert result.versions[0].components[0].ingredient_name == "Ingredient B"
    assert result.versions[1].components[0].ingredient_name == "Ingredient A"


def test_recipe_history_filters_by_active_at(db_session):
    product_id = _seed_recipe_history(db_session)

    with BoundSessionUnitOfWork(db_session) as uow:
        result = GetProductRecipeHistoryHandler().handle(
            GetProductRecipeHistoryQuery(
                product_id=product_id,
                active_at=datetime(2026, 1, 15, 12, 0, 0),
                date_from=None,
                date_to=None,
            ),
            uow,
        )

    assert len(result.versions) == 1
    assert result.versions[0].version == 1
