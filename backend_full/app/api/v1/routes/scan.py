from typing import Callable

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps.auth import PermissionChecker, get_db
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.serial.scan import (
    GetProductItemHistoryHandler,
    GetProductItemHistoryQuery,
    ListProductItemsHandler,
    ListProductItemsQuery,
    ScanQrCommand,
    ScanQrHandler,
)
from app.infrastructure.db.uow import BoundSessionUnitOfWork
from app.schemas import serial as schemas
from sqlalchemy.orm import Session

router = APIRouter(prefix="/scan", tags=["serial-scan"])


@router.get("/items", response_model=list[schemas.ProductItemListOut])
def list_product_items(
    status: str | None = Query(default=None),
    location_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    lot_id: int | None = Query(default=None),
    box_id: int | None = Query(default=None),
    reserved_transfer_doc_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["qr.scan"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(
        uow_factory,
        ListProductItemsHandler(),
        ListProductItemsQuery(
            status=status,
            location_id=location_id,
            product_id=product_id,
            lot_id=lot_id,
            box_id=box_id,
            reserved_transfer_doc_id=reserved_transfer_doc_id,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/items/{product_item_id}/history", response_model=schemas.ProductItemHistoryOut)
def get_product_item_history(
    product_item_id: int,
    user=Depends(PermissionChecker(["qr.scan"])),
    db: Session = Depends(get_db),
):
    with BoundSessionUnitOfWork(db) as uow:
        return GetProductItemHistoryHandler().handle(GetProductItemHistoryQuery(product_item_id=product_item_id), uow)


@router.post("/{qr_code}", response_model=schemas.ScanOut)
def scan_qr(
    qr_code: str,
    user=Depends(PermissionChecker(["qr.scan"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(uow_factory, ScanQrHandler(), ScanQrCommand(qr_code=qr_code))
