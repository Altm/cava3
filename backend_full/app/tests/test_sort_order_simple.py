from app.models.models import ProductAttribute, ProductType


def test_sort_order_create_with_custom_value(db_session):
    product_type = ProductType(name="Type A", description="A", is_composite=False)
    db_session.add(product_type)
    db_session.flush()

    attr = ProductAttribute(
        product_type_id=product_type.id,
        name="Attr",
        code="attr",
        data_type="string",
        is_required=False,
        sort_order=2,
    )
    db_session.add(attr)
    db_session.commit()

    saved = db_session.query(ProductAttribute).one()
    assert saved.sort_order == 2


def test_sort_order_default_value(db_session):
    product_type = ProductType(name="Type B", description="B", is_composite=False)
    db_session.add(product_type)
    db_session.flush()

    attr = ProductAttribute(
        product_type_id=product_type.id,
        name="Attr Default",
        code="attr_default",
        data_type="string",
        is_required=False,
    )
    db_session.add(attr)
    db_session.commit()

    saved = db_session.query(ProductAttribute).one()
    assert saved.sort_order == 1
