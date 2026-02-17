from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.simple import ProductAttributeValueCreate


def test_schema_accepts_new_field_name():
    schema = ProductAttributeValueCreate(product_attribute_id=1, value=Decimal("10.50"))
    assert schema.product_attribute_id == 1
    assert schema.value == Decimal("10.50")


def test_schema_rejects_old_field_name():
    with pytest.raises(ValidationError):
        ProductAttributeValueCreate(attribute_definition_id=1, value="legacy")
