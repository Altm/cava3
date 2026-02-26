from __future__ import annotations

from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.models import Stock, Product
from fastapi import HTTPException


class SerialStockLedger:
    """
    Compatibility layer for aggregated `stock`.

    Serialized documents (receipt/transfer/inventory) update `stock` as a cache so
    existing UI and analytics keep working without refactoring the old subsystem.
    """

    def __init__(self, db: Session):
        self.db = db

    def adjust_base_units(self, location_id: int, product_id: int, delta_base_units: int) -> Stock:
        """
        Apply +/- delta in product base units.

        Rules:
        - Creates stock row if missing.
        - Never allows aggregated stock to go negative.
        """
        if delta_base_units == 0:
            stock = self.db.query(Stock).filter_by(location_id=location_id, product_id=product_id).first()
            if not stock:
                product = self.db.get(Product, product_id)
                if not product:
                    raise HTTPException(status_code=404, detail="Product not found")
                stock = Stock(location_id=location_id, product_id=product_id, unit_id=product.base_unit_id, quantity=Decimal("0"))
                self.db.add(stock)
            return stock

        product = self.db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        delta = Decimal(delta_base_units)
        q = self.db.query(Stock).filter_by(location_id=location_id, product_id=product_id)
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            q = q.with_for_update()
        stock = q.first()
        if not stock:
            stock = Stock(location_id=location_id, product_id=product_id, unit_id=product.base_unit_id, quantity=Decimal("0"))
            self.db.add(stock)
            self.db.flush()

        new_qty = Decimal(stock.quantity) + delta
        if new_qty < 0:
            raise HTTPException(status_code=409, detail="Insufficient aggregated stock")
        stock.quantity = new_qty
        stock.unit_id = product.base_unit_id
        return stock
