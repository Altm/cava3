from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.application.common.uow import AbstractUnitOfWork
from app.services.stock_service import StockService


@dataclass(frozen=True)
class AdjustStockCommand:
    location_id: int
    product_id: int
    quantity: Decimal
    unit_id: int


class AdjustStockHandler:
    def handle(self, command: AdjustStockCommand, uow: AbstractUnitOfWork) -> dict:
        service = StockService(uow.session)
        stock = service.adjust_stock(
            location_id=command.location_id,
            product_id=command.product_id,
            quantity=command.quantity,
            unit_id=command.unit_id,
        )
        return {"product_id": stock.product_id, "location_id": stock.location_id, "quantity": float(stock.quantity)}
