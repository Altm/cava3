#!/usr/bin/env python3
"""
Test script to verify the product_attribute_id field rename in ProductAttributeValue
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.models.models import ProductAttributeValue
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_product_attribute_id_field():
    """Test that the product_attribute_id field is correctly renamed in ProductAttributeValue model"""
    print("Testing product_attribute_id field rename in ProductAttributeValue model...")
    
    # Create an in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Import Base from the main module
    from app.infrastructure.db.base import Base
    Base.metadata.create_all(engine)
    
    print("✓ Model compiled successfully with product_attribute_id field")
    
    # Check that ProductAttributeValue has the product_attribute_id column
    from sqlalchemy.orm import class_mapper
    
    mapper = class_mapper(ProductAttributeValue)
    columns = [prop.key for prop in mapper.attrs]
    assert 'product_attribute_id' in columns, f"Expected 'product_attribute_id' column in ProductAttributeValue, got {columns}"
    print("✓ ProductAttributeValue model has product_attribute_id field")
    
    # Check that attribute_definition_id is no longer present
    assert 'attribute_definition_id' not in columns, f"'attribute_definition_id' column should not exist in ProductAttributeValue, but found in {columns}"
    print("✓ ProductAttributeValue model no longer has attribute_definition_id field")
    
    # Test creating an instance to make sure it works
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create mock instances for foreign key constraints
    from app.models.models import Product, ProductAttribute, ProductType
    from decimal import Decimal
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Create a ProductType first
    product_type = ProductType(name="Test Type", description="Test", is_composite=False)
    session.add(product_type)
    session.commit()
    
    # Create a ProductAttribute
    product_attr = ProductAttribute(
        product_type_id=product_type.id,
        name="Test Attribute",
        code="test_attr",
        data_type="string",
        is_required=False,
        sort_order=1
    )
    session.add(product_attr)
    session.commit()
    
    # Create a Product
    product = Product(
        name="Test Product",
        sku="TEST001",
        primary_category="test",
        product_type_id=product_type.id,
        base_unit_id=1,
        unit_cost=Decimal("10.00")
    )
    session.add(product)
    session.commit()
    
    # Now create a ProductAttributeValue instance with the new field name
    attr_value = ProductAttributeValue(
        product_id=product.id,
        product_attribute_id=product_attr.id,
        value_string="Test Value"
    )
    
    session.add(attr_value)
    session.commit()
    
    # Retrieve and verify
    retrieved_attr_value = session.query(ProductAttributeValue).first()
    assert retrieved_attr_value is not None, "Could not retrieve ProductAttributeValue"
    assert retrieved_attr_value.product_attribute_id == product_attr.id, f"Expected product_attribute_id {product_attr.id}, got {retrieved_attr_value.product_attribute_id}"
    print("✓ ProductAttributeValue can be created and retrieved with product_attribute_id field")
    
    session.close()
    
    print("\n🎉 All tests passed! The attribute_definition_id field has been successfully renamed to product_attribute_id in product_attribute_value table.")


if __name__ == "__main__":
    test_product_attribute_id_field()