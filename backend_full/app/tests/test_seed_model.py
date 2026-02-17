from decimal import Decimal

from sqlalchemy.orm import class_mapper

from app.models.models import Product, ProductMeta, ProductType, Unit


def test_product_meta_model_structure():
    assert ProductMeta.__tablename__ == "product_meta"
    attrs = {prop.key for prop in class_mapper(ProductMeta).attrs}
    for field in (
        "id",
        "product_id",
        "old_id",
        "handle",
        "body_html",
        "vendor",
        "type",
        "tags",
        "published",
        "variant_barcode",
        "seo_title",
        "seo_description",
        "google_shopping",
        "image",
        "product",
    ):
        assert field in attrs

    product_attrs = {prop.key for prop in class_mapper(Product).attrs}
    assert "meta" in product_attrs


def test_product_meta_create_and_read(db_session):
    unit = Unit(code="unit", description="Unit", unit_type="base", is_discrete=True)
    db_session.add(unit)
    db_session.flush()

    product_type = ProductType(name="Wine Type", description="Type", is_composite=False)
    db_session.add(product_type)
    db_session.flush()

    product = Product(
        name="Test Wine",
        sku="TEST-WINE-001",
        product_type_id=product_type.id,
        base_cost=Decimal("10.00"),
        primary_category="wine",
        is_active=True,
        base_unit_id=unit.id,
    )
    db_session.add(product)
    db_session.flush()

    meta = ProductMeta(
        product_id=product.id,
        old_id=123,
        handle="test-wine-handle",
        vendor="Test Vendor",
        published=True,
    )
    db_session.add(meta)
    db_session.commit()

    saved = db_session.query(ProductMeta).one()
    assert saved.handle == "test-wine-handle"
