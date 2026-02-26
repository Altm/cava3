from decimal import Decimal
from datetime import datetime

from app.application.simple_catalog.common import ProductAvailabilityCalculator, serialize_product, serialize_product_view
from app.models.models import (
    Ingredient,
    IngredientProductBinding,
    Location,
    Product,
    ProductRecipe,
    ProductRecipeComponent,
    ProductType,
    Stock,
    Unit,
)


def seed_recursive_composites(db_session):
    unit = Unit(code="pcs", description="Pieces", unit_type="base", is_discrete=True)
    simple_type = ProductType(name="simple_type", is_composite=False)
    composite_type = ProductType(name="composite_type", is_composite=True)
    location = Location(name="Warehouse Composite", code="warehouse-composite")
    db_session.add_all([unit, simple_type, composite_type, location])
    db_session.flush()

    component_a = Product(
        name="Component A",
        sku="CMP-A",
        primary_category="simple",
        product_type_id=simple_type.id,
        base_unit_id=unit.id,
        is_active=True,
    )
    component_b = Product(
        name="Component B",
        sku="CMP-B",
        primary_category="simple",
        product_type_id=simple_type.id,
        base_unit_id=unit.id,
        is_active=True,
    )
    combo = Product(
        name="Combo",
        sku="COMBO-1",
        primary_category="combo",
        product_type_id=composite_type.id,
        base_unit_id=unit.id,
        is_active=True,
    )
    super_combo = Product(
        name="Super Combo",
        sku="COMBO-2",
        primary_category="combo",
        product_type_id=composite_type.id,
        base_unit_id=unit.id,
        is_active=True,
    )
    db_session.add_all([component_a, component_b, combo, super_combo])
    db_session.flush()

    ing_a = Ingredient(code="ing_cmp_a", name="Ingredient A", base_unit_id=unit.id, is_active=True)
    ing_b = Ingredient(code="ing_cmp_b", name="Ingredient B", base_unit_id=unit.id, is_active=True)
    ing_combo = Ingredient(code="ing_combo", name="Ingredient Combo", base_unit_id=unit.id, is_active=True)
    db_session.add_all([ing_a, ing_b, ing_combo])
    db_session.flush()

    db_session.add_all(
        [
            IngredientProductBinding(
                ingredient_id=ing_a.id,
                product_id=component_a.id,
                ratio_to_ingredient_base=Decimal("1"),
                priority=100,
                is_active=True,
            ),
            IngredientProductBinding(
                ingredient_id=ing_b.id,
                product_id=component_b.id,
                ratio_to_ingredient_base=Decimal("1"),
                priority=100,
                is_active=True,
            ),
            IngredientProductBinding(
                ingredient_id=ing_combo.id,
                product_id=combo.id,
                ratio_to_ingredient_base=Decimal("1"),
                priority=100,
                is_active=True,
            ),
        ]
    )
    db_session.flush()

    now = datetime.utcnow()
    combo_recipe = ProductRecipe(
        product_id=combo.id,
        version=1,
        is_active=True,
        valid_from=now,
        valid_to=None,
    )
    super_recipe = ProductRecipe(
        product_id=super_combo.id,
        version=1,
        is_active=True,
        valid_from=now,
        valid_to=None,
    )
    db_session.add_all([combo_recipe, super_recipe])
    db_session.flush()

    db_session.add_all(
        [
            ProductRecipeComponent(
                recipe_id=combo_recipe.id,
                ingredient_id=ing_a.id,
                quantity=Decimal("2"),
                unit_id=unit.id,
            ),
            ProductRecipeComponent(
                recipe_id=combo_recipe.id,
                ingredient_id=ing_b.id,
                quantity=Decimal("3"),
                unit_id=unit.id,
            ),
            ProductRecipeComponent(
                recipe_id=super_recipe.id,
                ingredient_id=ing_combo.id,
                quantity=Decimal("1"),
                unit_id=unit.id,
            ),
            ProductRecipeComponent(
                recipe_id=super_recipe.id,
                ingredient_id=ing_a.id,
                quantity=Decimal("4"),
                unit_id=unit.id,
            ),
        ]
    )

    db_session.add_all(
        [
            Stock(location_id=location.id, product_id=component_a.id, quantity=Decimal("10"), unit_id=unit.id),
            Stock(location_id=location.id, product_id=component_b.id, quantity=Decimal("6"), unit_id=unit.id),
            Stock(location_id=location.id, product_id=combo.id, quantity=Decimal("100"), unit_id=unit.id),
        ]
    )
    db_session.commit()
    return component_a, component_b, combo, super_combo


def test_recursive_composite_availability_is_component_based(db_session):
    _, _, combo, super_combo = seed_recursive_composites(db_session)

    calculator = ProductAvailabilityCalculator(db_session)
    combo_available = calculator.available_quantity(combo.id)
    super_available = calculator.available_quantity(super_combo.id)

    assert combo_available == Decimal("2")
    assert super_available == Decimal("2")

    combo_out = serialize_product(combo, db_session, calculator=calculator)
    super_out = serialize_product(super_combo, db_session, calculator=calculator)
    assert combo_out.stock == Decimal("2")
    assert super_out.stock == Decimal("2")


def test_recursive_component_tree_is_returned_for_product_view(db_session):
    _, _, combo, super_combo = seed_recursive_composites(db_session)
    calculator = ProductAvailabilityCalculator(db_session)

    view = serialize_product_view(super_combo, db_session, calculator=calculator)
    assert len(view.component_tree) == 2

    combo_node = next(node for node in view.component_tree if node.bound_product_id == combo.id)
    assert combo_node.bound_product_is_composite is True
    assert combo_node.available_quantity == Decimal("2")
    assert {node.ingredient_name for node in combo_node.children} == {"Ingredient A", "Ingredient B"}


def test_composite_zero_stock_is_not_serialized_in_scientific_notation(db_session):
    unit = Unit(code="pcs_zero", description="Pieces", unit_type="base", is_discrete=True)
    simple_type = ProductType(name="simple_zero", is_composite=False)
    composite_type = ProductType(name="composite_zero", is_composite=True)
    location = Location(name="Warehouse Zero", code="warehouse-zero")
    db_session.add_all([unit, simple_type, composite_type, location])
    db_session.flush()

    component = Product(
        name="Component Zero",
        sku="CMP-ZERO",
        primary_category="simple",
        product_type_id=simple_type.id,
        base_unit_id=unit.id,
        is_active=True,
    )
    composite = Product(
        name="Composite Zero",
        sku="COMPOSITE-ZERO",
        primary_category="combo",
        product_type_id=composite_type.id,
        base_unit_id=unit.id,
        is_active=True,
    )
    db_session.add_all([component, composite])
    db_session.flush()

    ingredient = Ingredient(code="ing_zero_component", name="Zero Component", base_unit_id=unit.id, is_active=True)
    db_session.add(ingredient)
    db_session.flush()
    db_session.add(
        IngredientProductBinding(
            ingredient_id=ingredient.id,
            product_id=component.id,
            ratio_to_ingredient_base=Decimal("1"),
            priority=100,
            is_active=True,
        )
    )
    recipe = ProductRecipe(
        product_id=composite.id,
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
            quantity=Decimal("0.000001"),
            unit_id=unit.id,
        )
    )
    db_session.add(
        Stock(
            location_id=location.id,
            product_id=component.id,
            quantity=Decimal("0"),
            unit_id=unit.id,
        )
    )
    db_session.flush()

    calculator = ProductAvailabilityCalculator(db_session)
    available = calculator.available_quantity(composite.id)
    serialized = serialize_product(composite, db_session, calculator=calculator)

    assert available == Decimal("0")
    assert str(available) == "0"
    assert serialized.stock == Decimal("0")
    assert str(serialized.stock) == "0"
