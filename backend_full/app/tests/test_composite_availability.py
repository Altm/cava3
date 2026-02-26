from decimal import Decimal

from app.application.simple_catalog.common import ProductAvailabilityCalculator, serialize_product, serialize_product_view
from app.models.models import Location, Product, ProductComposite, ProductType, Stock, Unit


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

    db_session.add_all(
        [
            ProductComposite(
                parent_product_id=combo.id,
                component_product_id=component_a.id,
                quantity=Decimal("2"),
                unit_id=unit.id,
            ),
            ProductComposite(
                parent_product_id=combo.id,
                component_product_id=component_b.id,
                quantity=Decimal("3"),
                unit_id=unit.id,
            ),
            ProductComposite(
                parent_product_id=super_combo.id,
                component_product_id=combo.id,
                quantity=Decimal("1"),
                unit_id=unit.id,
            ),
            ProductComposite(
                parent_product_id=super_combo.id,
                component_product_id=component_a.id,
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
    component_a, component_b, combo, super_combo = seed_recursive_composites(db_session)
    calculator = ProductAvailabilityCalculator(db_session)

    view = serialize_product_view(super_combo, db_session, calculator=calculator)
    assert len(view.component_tree) == 2

    combo_node = next(node for node in view.component_tree if node.component_product_id == combo.id)
    assert combo_node.is_composite is True
    assert combo_node.available_quantity == Decimal("2")
    assert {node.component_product_id for node in combo_node.children} == {component_a.id, component_b.id}


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

    db_session.add(
        ProductComposite(
            parent_product_id=composite.id,
            component_product_id=component.id,
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
