from decimal import Decimal

from app.models.models import Product, ProductAttribute, ProductAttributeValue, ProductType, Unit


def test_attribute_definition_alias_relationship(db_session):
    unit = Unit(code="piece", description="Piece", unit_type="base", is_discrete=True)
    db_session.add(unit)
    db_session.flush()

    product_type = ProductType(name="Spirits", description="Spirits type", is_composite=False)
    db_session.add(product_type)
    db_session.flush()

    product_attribute = ProductAttribute(
        product_type_id=product_type.id,
        name="Year",
        code="year",
        data_type="number",
        is_required=False,
        sort_order=2,
    )
    db_session.add(product_attribute)
    db_session.flush()

    product = Product(
        name="Whiskey",
        sku="WHISKEY-001",
        primary_category="spirits",
        product_type_id=product_type.id,
        base_unit_id=unit.id,
        base_cost=Decimal("15.00"),
    )
    db_session.add(product)
    db_session.flush()

    attribute_value = ProductAttributeValue(
        product_id=product.id,
        product_attribute_id=product_attribute.id,
        value_number=Decimal("2020"),
    )
    db_session.add(attribute_value)
    db_session.commit()

    saved = db_session.query(ProductAttributeValue).first()
    assert saved is not None
    assert saved.attribute_definition is not None
    assert saved.attribute_definition.id == product_attribute.id
