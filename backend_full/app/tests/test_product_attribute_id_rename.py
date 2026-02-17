from decimal import Decimal

from app.models.models import Product, ProductAttribute, ProductAttributeValue, ProductType, Unit


def test_product_attribute_id_field(db_session):
    unit = Unit(code="bottle", description="Bottle", unit_type="base", is_discrete=True)
    db_session.add(unit)
    db_session.flush()

    product_type = ProductType(name="Wine", description="Wine type", is_composite=False)
    db_session.add(product_type)
    db_session.flush()

    product_attribute = ProductAttribute(
        product_type_id=product_type.id,
        name="Region",
        code="region",
        data_type="string",
        is_required=False,
        sort_order=1,
    )
    db_session.add(product_attribute)
    db_session.flush()

    product = Product(
        name="Chianti",
        sku="CHIANTI-001",
        primary_category="wine",
        product_type_id=product_type.id,
        base_unit_id=unit.id,
        base_cost=Decimal("10.00"),
    )
    db_session.add(product)
    db_session.flush()

    attribute_value = ProductAttributeValue(
        product_id=product.id,
        product_attribute_id=product_attribute.id,
        value_string="Tuscany",
    )
    db_session.add(attribute_value)
    db_session.commit()

    saved = db_session.query(ProductAttributeValue).first()
    assert saved is not None
    assert saved.product_attribute_id == product_attribute.id
    assert saved.product_id == product.id
