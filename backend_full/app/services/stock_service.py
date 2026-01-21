from decimal import Decimal
from sqlalchemy.orm import Session
from app.common.errors import ValidationError
from app.models.models import Stock, Product
from app.services.units import UnitConverter


class StockService:
    """Manages stock mutations and validations."""

    def __init__(self, db: Session):
        self.db = db
        self.converter = UnitConverter(db)

    def adjust_stock(self, location_id: int, product_id: int, quantity: Decimal, unit_code: str) -> Stock:
        product = self.db.query(Product).get(product_id)
        if not product:
            raise ValidationError("Product missing")
        quantity_base = self.converter.to_base(unit_code, quantity, product.base_unit_code)
        stock = self.db.query(Stock).filter_by(location_id=location_id, product_id=product_id).first()
        if not stock:
            stock = Stock(location_id=location_id, product_id=product_id, unit_code=product.base_unit_code, quantity=Decimal("0"))
            self.db.add(stock)
        new_qty = stock.quantity + quantity_base
        if new_qty < 0:
            raise ValidationError("Insufficient stock")
        stock.quantity = self.converter.normalize(product.base_unit_code, new_qty)
        return stock
