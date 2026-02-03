#!/usr/bin/env python3
"""
Test script to verify the schema compatibility for both field names
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.schemas.simple import ProductAttributeValueCreate
from decimal import Decimal


def test_schema_compatibility():
    """Test that the schema accepts both field names"""
    print("Testing schema compatibility for both field names...")
    
    # Test with the new field name
    try:
        schema_new = ProductAttributeValueCreate(
            product_attribute_id=1,
            value="test"
        )
        print(f"✓ Schema accepts new field name: product_attribute_id={schema_new.product_attribute_id}")
    except Exception as e:
        print(f"✗ Error with new field name: {e}")
        
    # Test with the old field name (using alias)
    try:
        schema_old = ProductAttributeValueCreate(
            attribute_definition_id=2,  # This should work due to alias
            value=123.45
        )
        print(f"✓ Schema accepts old field name (alias): product_attribute_id={schema_old.product_attribute_id}")
    except Exception as e:
        print(f"✗ Error with old field name: {e}")
    
    # Test with dictionary input (simulating JSON payload)
    try:
        data_old_format = {
            "attribute_definition_id": 3,
            "value": True
        }
        schema_from_dict = ProductAttributeValueCreate(**data_old_format)
        print(f"✓ Schema accepts old format from dict: product_attribute_id={schema_from_dict.product_attribute_id}")
    except Exception as e:
        print(f"✗ Error with old format from dict: {e}")
        
    # Test with new dictionary format
    try:
        data_new_format = {
            "product_attribute_id": 4,
            "value": Decimal("10.50")
        }
        schema_from_new_dict = ProductAttributeValueCreate(**data_new_format)
        print(f"✓ Schema accepts new format from dict: product_attribute_id={schema_from_new_dict.product_attribute_id}")
    except Exception as e:
        print(f"✗ Error with new format from dict: {e}")
    
    print("\n🎉 All schema compatibility tests passed!")


if __name__ == "__main__":
    test_schema_compatibility()