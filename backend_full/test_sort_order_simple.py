#!/usr/bin/env python3
"""
Simple test script to verify the sort_order field addition to product_attribute
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.models.models import ProductAttribute
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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
    
    # Test creating an instance to make sure it works
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create a mock ProductType for the foreign key constraint
    from app.models.models import ProductType
    Base.metadata.create_all(engine)  # Ensure all tables are created
    
    # Create a ProductType instance first
    product_type = ProductType(name="Test Type", description="Test", is_composite=False)
    session.add(product_type)
    session.commit()
    
    # Now create a ProductAttribute instance
    attr = ProductAttribute(
        product_type_id=product_type.id,
        name="Test Attribute",
        code="test_attr",
        data_type="string",
        is_required=False,
        sort_order=2  # Explicitly set sort_order
    )
    
    session.add(attr)
    session.commit()
    
    # Retrieve and verify
    retrieved_attr = session.query(ProductAttribute).first()
    assert retrieved_attr is not None, "Could not retrieve ProductAttribute"
    assert retrieved_attr.sort_order == 2, f"Expected sort_order 2, got {retrieved_attr.sort_order}"
    print("✓ ProductAttribute can be created and retrieved with sort_order field")
    
    session.close()
    
    print("\n🎉 All tests passed! The sort_order field has been successfully added to product_attribute table.")


if __name__ == "__main__":
    test_sort_order_field()