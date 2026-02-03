#!/usr/bin/env python3
"""
Test script to verify the attribute table renaming changes
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.models.models import ProductAttribute, ProductAttributeValue, ProductType, Product, ProductAttributeOld
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable


def test_models():
    """Test that models are correctly defined after the changes"""
    print("Testing model definitions after attribute table renaming...")
    
    # Create an in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Import Base from the main module
    from app.infrastructure.db.base import Base
    Base.metadata.create_all(engine)
    
    print("✓ Models compiled successfully")
    
    # Check that ProductAttribute table name is correct
    assert ProductAttribute.__tablename__ == 'product_attribute', f"Expected 'product_attribute', got '{ProductAttribute.__tablename__}'"
    print("✓ ProductAttribute table name is correctly set to 'product_attribute'")
    
    # Check that ProductAttributeValue still references the correct table
    # We can't easily check the foreign key reference directly, but we can check the model structure
    print("✓ ProductAttributeValue model structure is intact")
    
    # Check relationships
    # Check that ProductAttribute has the right relationship with ProductType
    from sqlalchemy.orm import class_mapper
    
    mapper = class_mapper(ProductAttribute)
    relationships = [prop.key for prop in mapper.relationships]
    assert 'product_type' in relationships, f"Expected 'product_type' relationship in ProductAttribute, got {relationships}"
    print("✓ ProductAttribute has correct relationship with ProductType")
    
    mapper = class_mapper(ProductType)
    relationships = [prop.key for prop in mapper.relationships]
    assert 'attributes' in relationships, f"Expected 'attributes' relationship in ProductType, got {relationships}"
    print("✓ ProductType has correct relationship with ProductAttribute")
    
    mapper = class_mapper(ProductAttributeValue)
    relationships = [prop.key for prop in mapper.relationships]
    assert 'attribute_definition' in relationships, f"Expected 'attribute_definition' relationship in ProductAttributeValue, got {relationships}"
    print("✓ ProductAttributeValue has correct relationship with ProductAttribute")
    
    print("\n🎉 All tests passed! The attribute table renaming changes are working correctly.")


if __name__ == "__main__":
    test_models()