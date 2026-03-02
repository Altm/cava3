from decimal import Decimal
from typing import Callable

from fastapi import APIRouter, Depends

from app.api.v1.deps.auth import PermissionChecker
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command
from app.application.common.uow import AbstractUnitOfWork
from app.application.stock.commands import AdjustStockCommand, AdjustStockHandler
from app.schemas.legacy import StockAdjustIn

router = APIRouter(prefix="/stock", tags=["stock"])


@router.post("/adjust")
def adjust_stock(
    payload: StockAdjustIn,
    user=Depends(PermissionChecker(["stock.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Выполняет ручную корректировку остатков по товару и локации."""
    return dispatch_command(
        uow_factory,
        AdjustStockHandler(),
        AdjustStockCommand(
            location_id=payload.location_id,
            product_id=payload.product_id,
            quantity=Decimal(str(payload.quantity)),
            unit_id=payload.unit_id,
        ),
    )
