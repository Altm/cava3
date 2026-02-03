#!/usr/bin/env python3
"""
Test script to verify the sort_order field addition to product_attribute
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.models.models import ProductAttribute
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable


def test_sort_order_field():
    """Test that the sort_order field is correctly added to ProductAttribute model"""
    print("Testing sort_order field addition to ProductAttribute model...")
    
    # Create an in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Import Base from the main module
    from app.infrastructure.db.base import Base
    Base.metadata.create_all(engine)
    
    print("✓ Model compiled successfully with sort_order field")
    
    # Check that ProductAttribute has the sort_order column
    from sqlalchemy.orm import class_mapper
    
    mapper = class_mapper(ProductAttribute)
    columns = [prop.key for prop in mapper.attrs]
    assert 'sort_order' in columns, f"Expected 'sort_order' column in ProductAttribute, got {columns}"
    print("✓ ProductAttribute model has sort_order field")
    
    # Check the column properties
    from sqlalchemy import inspect
    inspector = inspect(engine)
    columns_info = inspector.get_columns('product_attribute')
    
    sort_order_col = None
    for col in columns_info:
        if col['name'] == 'sort_order':
            sort_order_col = col
            break
    
    assert sort_order_col is not None, "sort_order column not found in database table"
    print("✓ sort_order column exists in database table")
    
    # Check that it's an integer type
    from sqlalchemy.types import Integer
    assert isinstance(sort_order_col['type'], Integer), f"Expected Integer type for sort_order, got {type(sort_order_col['type'])}"
    print("✓ sort_order column has correct Integer type")
    
    # Check that it has a default value
    assert sort_order_col['default'] is not None, "sort_order column should have a default value"
    print("✓ sort_order column has default value")
    
    print("\n🎉 All tests passed! The sort_order field has been successfully added to product_attribute table.")


if __name__ == "__main__":
    test_sort_order_field()