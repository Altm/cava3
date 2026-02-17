from sqlalchemy.types import Integer

from app.models.models import ProductAttribute


def test_sort_order_column_definition():
    column = ProductAttribute.__table__.c.sort_order
    assert isinstance(column.type, Integer)
    assert column.nullable is False
    assert column.default is not None
    assert column.server_default is not None
