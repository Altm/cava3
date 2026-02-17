from sqlalchemy.orm import class_mapper

from app.models.models import ProductAttribute, ProductAttributeValue, ProductType


def test_attribute_model_structure():
    assert ProductAttribute.__tablename__ == "product_attribute"

    product_attribute_rels = {prop.key for prop in class_mapper(ProductAttribute).relationships}
    assert "product_type" in product_attribute_rels

    product_type_rels = {prop.key for prop in class_mapper(ProductType).relationships}
    assert "attributes" in product_type_rels

    attribute_value_rels = {prop.key for prop in class_mapper(ProductAttributeValue).relationships}
    assert "product_attribute" in attribute_value_rels
    assert "attribute_definition" in attribute_value_rels
