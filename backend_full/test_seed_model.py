#!/usr/bin/env python3
"""
Test script to verify the new model and migration work correctly
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.models.models import ProductMeta, Product
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_new_model():
    """Test that the new ProductMeta model works correctly"""
    print("Testing ProductMeta model...")
    
    # Create an in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Import Base from the main module
    from app.infrastructure.db.base import Base
    Base.metadata.create_all(engine)
    
    print("✓ Model compiled successfully with ProductMeta")
    
    # Check that ProductMeta has the correct table name
    assert ProductMeta.__tablename__ == 'product_meta', f"Expected 'product_meta', got '{ProductMeta.__tablename__}'"
    print("✓ ProductMeta has correct table name")
    
    # Check that ProductMeta has the correct columns
    from sqlalchemy.orm import class_mapper
    
    mapper = class_mapper(ProductMeta)
    columns = [prop.key for prop in mapper.attrs]
    expected_columns = ['id', 'product_id', 'old_id', 'handle', 'body_html', 'vendor', 'type', 
                      'tags', 'published', 'variant_barcode', 'seo_title', 'seo_description', 
                      'google_shopping', 'image', 'product']
    for col in expected_columns:
        assert col in columns, f"Expected '{col}' column in ProductMeta, got {columns}"
    print("✓ ProductMeta has all expected columns")
    
    # Check that Product has the meta relationship
    product_mapper = class_mapper(Product)
    product_columns = [prop.key for prop in product_mapper.attrs]
    assert 'meta' in product_columns, f"Expected 'meta' relationship in Product, got {product_columns}"
    print("✓ Product has meta relationship")
    
    # Test creating an instance to make sure it works
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create a mock Product first
    product = Product(
        name="Test Wine",
        sku="TEST001",  # SKU is required
        product_type_id=1,
        unit_cost=10.0,
        primary_category="Wine",
        is_active=True,
        base_unit_id=1
    )
    session.add(product)
    session.commit()
    
    # Now create a ProductMeta instance
    meta = ProductMeta(
        product_id=product.id,
        old_id=123,
        handle="test-wine-handle",
        vendor="Test Vendor",
        published=True
    )
    
    session.add(meta)
    session.commit()
    
    # Retrieve and verify
    retrieved_meta = session.query(ProductMeta).first()
    assert retrieved_meta is not None, "Could not retrieve ProductMeta"
    assert retrieved_meta.handle == "test-wine-handle", f"Expected 'test-wine-handle', got '{retrieved_meta.handle}'"
    print("✓ ProductMeta can be created and retrieved")
    
    session.close()
    
    print("\n🎉 All tests passed! The new model and migration are working correctly.")


if __name__ == "__main__":
    test_new_model()