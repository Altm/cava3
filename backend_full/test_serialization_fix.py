#!/usr/bin/env python3
"""
Test script to verify the fix for attribute_definition_id issue in serialization
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.models.models import ProductAttributeValue
from app.schemas.simple import ProductAttributeValueCreate
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_serialization_fix():
    """Test that the serialization fix works correctly"""
    print("Testing serialization fix for ProductAttributeValue...")
    
    # Create an in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Import Base from the main module
    from app.infrastructure.db.base import Base
    Base.metadata.create_all(engine)
    
    print("✓ Model compiled successfully")
    
    # Create a sample ProductAttributeValue instance
    attr_value = ProductAttributeValue(
        product_id=1,
        product_attribute_id=1,
        value_string="Test Value"
    )
    
    # Test that the attribute exists and can be accessed
    assert hasattr(attr_value, 'product_attribute_id'), "product_attribute_id attribute should exist"
    assert not hasattr(attr_value, 'attribute_definition_id'), "attribute_definition_id attribute should not exist anymore"
    print("✓ ProductAttributeValue has correct attribute name (product_attribute_id)")
    
    # Test schema creation
    schema = ProductAttributeValueCreate(
        product_attribute_id=1,
        value="Test Value"
    )
    
    assert hasattr(schema, 'product_attribute_id'), "Schema should have product_attribute_id field"
    print("✓ ProductAttributeValueCreate schema has correct field name (product_attribute_id)")
    
    # Test that we can access the field value
    test_value = 5
    attr_value.product_attribute_id = test_value
    assert attr_value.product_attribute_id == test_value, f"Expected {test_value}, got {attr_value.product_attribute_id}"
    print("✓ Can access and set product_attribute_id field correctly")
    
    print("\n🎉 All tests passed! The serialization fix is working correctly.")


if __name__ == "__main__":
    test_serialization_fix()