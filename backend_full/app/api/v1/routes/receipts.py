from typing import Callable

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import PermissionChecker, get_db
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.serial.receipts import (
    AddReceiptLineCommand,
    AddReceiptLineHandler,
    CreateReceiptCommand,
    CreateReceiptHandler,
    GenerateReceiptCommand,
    GenerateReceiptHandler,
    GetReceiptItemsHandler,
    GetReceiptItemsQuery,
    GetReceiptLinesHandler,
    GetReceiptLinesQuery,
    GetReceiptHandler,
    GetReceiptQuery,
    ListReceiptsHandler,
    ListReceiptsQuery,
    PostReceiptCommand,
    PostReceiptHandler,
    ReceiptAutoBoxCommand,
    ReceiptAutoBoxHandler,
    ReceiptItemLabelsHandler,
    ReceiptItemLabelsQuery,
    RemoveReceiptLineCommand,
    RemoveReceiptLineHandler,
    VoidReceiptCommand,
    VoidReceiptHandler,
)
from app.infrastructure.db.uow import BoundSessionUnitOfWork
from app.schemas import serial as schemas

router = APIRouter(prefix="/receipts", tags=["serial-receipts"])


@router.post("", response_model=schemas.ReceiptOut)
def create_receipt(
    payload: schemas.ReceiptCreate,
    user=Depends(PermissionChecker(["receipts.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        CreateReceiptHandler(),
        CreateReceiptCommand(payload=payload, created_by_user_id=getattr(user, "id", None)),
    )


@router.get("", response_model=list[schemas.ReceiptListOut])
def list_receipts(
    status: str | None = Query(default=None),
    to_location_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    created_by_user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["receipts.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(
        uow_factory,
        ListReceiptsHandler(),
        ListReceiptsQuery(
            status=status,
            to_location_id=to_location_id,
            product_id=product_id,
            created_by_user_id=created_by_user_id,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/{receipt_id}", response_model=schemas.ReceiptListOut)
def get_receipt(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, GetReceiptHandler(), GetReceiptQuery(receipt_id=receipt_id))


@router.get("/{receipt_id}/lines", response_model=list[schemas.ReceiptLineOut])
def get_receipt_lines(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, GetReceiptLinesHandler(), GetReceiptLinesQuery(receipt_id=receipt_id))


@router.get("/{receipt_id}/items", response_model=list[schemas.ReceiptItemContentOut])
def get_receipt_items(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.read"])),
    db: Session = Depends(get_db),
):
    with BoundSessionUnitOfWork(db) as uow:
        return GetReceiptItemsHandler().handle(GetReceiptItemsQuery(receipt_id=receipt_id), uow)


@router.post("/{receipt_id}/lines", response_model=schemas.ReceiptLineOut)
def add_receipt_line(
    receipt_id: int,
    payload: schemas.ReceiptLineCreate,
    user=Depends(PermissionChecker(["receipts.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        AddReceiptLineHandler(),
        AddReceiptLineCommand(receipt_id=receipt_id, payload=payload),
    )


@router.post("/{receipt_id}/lines/{line_id}/remove")
def remove_receipt_line(
    receipt_id: int,
    line_id: int,
    user=Depends(PermissionChecker(["receipts.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        RemoveReceiptLineHandler(),
        RemoveReceiptLineCommand(receipt_id=receipt_id, line_id=line_id),
    )


@router.post("/{receipt_id}/generate", response_model=schemas.ReceiptGenerateOut)
def generate_receipt(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        GenerateReceiptHandler(),
        GenerateReceiptCommand(receipt_id=receipt_id),
    )


@router.post("/{receipt_id}/post")
def post_receipt(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        PostReceiptHandler(),
        PostReceiptCommand(receipt_id=receipt_id),
    )


@router.post("/{receipt_id}/void")
def void_receipt(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        VoidReceiptHandler(),
        VoidReceiptCommand(receipt_id=receipt_id),
    )


@router.get("/{receipt_id}/labels/items", response_model=schemas.LabelsOut)
def receipt_item_labels(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(
        uow_factory,
        ReceiptItemLabelsHandler(),
        ReceiptItemLabelsQuery(receipt_id=receipt_id),
    )


@router.post("/{receipt_id}/auto-box", response_model=schemas.ReceiptAutoBoxOut)
def receipt_auto_box(
    receipt_id: int,
    payload: schemas.ReceiptAutoBoxRequest,
    user=Depends(PermissionChecker(["receipts.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        ReceiptAutoBoxHandler(),
        ReceiptAutoBoxCommand(receipt_id=receipt_id, payload=payload),
    )
