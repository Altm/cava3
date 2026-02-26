from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Product, ProductTypeUnit, ProductUnit, Stock


class StockService:
    """Manages aggregated stock mutations and validations (unit_id based)."""

    def __init__(self, db: Session):
        self.db = db

    def adjust_stock(self, location_id: int, product_id: int, quantity: Decimal, unit_id: int) -> Stock:
        """
        Adjust aggregated stock for a product in a location.

        Inputs:
        - `quantity`: may be fractional
        - `unit_id`: unit for `quantity`

        Storage:
        - Stock is stored in product base unit (`product.base_unit_id`).
        """
        product = self.db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product missing")

        qty_base = self._to_base(product_id=product.id, from_unit_id=unit_id, qty=quantity)

        q = self.db.query(Stock).filter_by(location_id=location_id, product_id=product_id)
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            q = q.with_for_update()
        stock = q.first()
        if not stock:
            stock = Stock(location_id=location_id, product_id=product_id, unit_id=product.base_unit_id, quantity=Decimal("0"))
            self.db.add(stock)
            self.db.flush()

        new_qty = Decimal(stock.quantity) + qty_base
        if new_qty < 0:
            raise HTTPException(status_code=409, detail="Insufficient stock")
        stock.quantity = new_qty
        stock.unit_id = product.base_unit_id
        return stock

    def _to_base(self, product_id: int, from_unit_id: int, qty: Decimal) -> Decimal:
        product = self.db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product missing")
        if from_unit_id == product.base_unit_id:
            return qty

        pu = (
            self.db.query(ProductUnit)
            .filter(ProductUnit.product_id == product_id, ProductUnit.unit_id == from_unit_id)
            .first()
        )
        if pu:
            ratio = Decimal(str(pu.ratio_to_base))
            return qty * ratio
        if product.product_type_id:
            type_unit = (
                self.db.query(ProductTypeUnit)
                .filter(
                    ProductTypeUnit.product_type_id == product.product_type_id,
                    ProductTypeUnit.unit_id == from_unit_id,
                )
                .first()
            )
            if type_unit:
                ratio = Decimal(str(type_unit.ratio_to_base))
                return qty * ratio
        raise HTTPException(status_code=422, detail="Missing product unit conversion")
