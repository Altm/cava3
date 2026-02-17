from typing import Callable

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import PermissionChecker, get_db
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.serial.transfers import (
    CloseTransferCommand,
    CloseTransferHandler,
    CreateTransferCommand,
    CreateTransferHandler,
    GetTransferHandler,
    GetTransferQuery,
    ListTransferItemsHandler,
    ListTransferItemsQuery,
    ListTransfersHandler,
    ListTransfersQuery,
    PlanTransferCommand,
    PlanTransferHandler,
    RemoveTransferItemCommand,
    RemoveTransferItemHandler,
    ScanTransferCommand,
    ScanTransferHandler,
    ShipTransferCommand,
    ShipTransferHandler,
)
from app.infrastructure.db.uow import BoundSessionUnitOfWork
from app.schemas import serial as schemas

router = APIRouter(prefix="/transfers", tags=["serial-transfers"])


@router.post("", response_model=schemas.TransferDocOut)
def create_transfer(
    payload: schemas.TransferCreate,
    user=Depends(PermissionChecker(["transfers.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт документ перемещения между локациями."""
    return dispatch_command(
        uow_factory,
        CreateTransferHandler(),
        CreateTransferCommand(payload=payload, created_by_user_id=getattr(user, "id", None)),
    )


@router.get("", response_model=list[schemas.TransferDocListOut])
def list_transfers(
    status: str | None = Query(default=None),
    from_location_id: int | None = Query(default=None),
    to_location_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    created_by_user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["transfers.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список документов перемещения с фильтрами."""
    return dispatch_query(
        uow_factory,
        ListTransfersHandler(),
        ListTransfersQuery(
            status=status,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            product_id=product_id,
            created_by_user_id=created_by_user_id,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/{transfer_doc_id}", response_model=schemas.TransferDocDetailOut)
def get_transfer(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает карточку документа перемещения."""
    return dispatch_query(uow_factory, GetTransferHandler(), GetTransferQuery(transfer_doc_id=transfer_doc_id))


@router.get("/{transfer_doc_id}/items", response_model=list[schemas.TransferItemMovementOut])
def list_transfer_items(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    """Возвращает список item, участвующих в перемещении."""
    with BoundSessionUnitOfWork(db) as uow:
        return ListTransferItemsHandler().handle(ListTransferItemsQuery(transfer_doc_id=transfer_doc_id), uow)


@router.post("/{transfer_doc_id}/plan", response_model=schemas.TransferPlanOut)
def plan_transfer(
    transfer_doc_id: int,
    payload: schemas.TransferPlan,
    user=Depends(PermissionChecker(["transfers.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Планирует отбор item по товару и количеству (FIFO)."""
    return dispatch_command(
        uow_factory,
        PlanTransferHandler(),
        PlanTransferCommand(transfer_doc_id=transfer_doc_id, payload=payload),
    )


@router.post("/{transfer_doc_id}/remove-item")
def remove_transfer_item(
    transfer_doc_id: int,
    payload: schemas.TransferRemoveItem,
    user=Depends(PermissionChecker(["transfers.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Удаляет item из плана перемещения."""
    return dispatch_command(
        uow_factory,
        RemoveTransferItemHandler(),
        RemoveTransferItemCommand(transfer_doc_id=transfer_doc_id, payload=payload),
    )


@router.post("/{transfer_doc_id}/scan")
def scan_transfer(
    transfer_doc_id: int,
    payload: schemas.TransferScan,
    user=Depends(PermissionChecker(["transfers.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Обрабатывает скан ITM/BOX на этапе отбора или приёмки."""
    return dispatch_command(
        uow_factory,
        ScanTransferHandler(),
        ScanTransferCommand(transfer_doc_id=transfer_doc_id, payload=payload),
    )


@router.post("/{transfer_doc_id}/ship")
def ship_transfer(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Переводит документ в статус отгрузки."""
    return dispatch_command(
        uow_factory,
        ShipTransferHandler(),
        ShipTransferCommand(transfer_doc_id=transfer_doc_id),
    )


@router.post("/{transfer_doc_id}/close")
def close_transfer(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Закрывает перемещение и списывает неполученные item как lost."""
    return dispatch_command(
        uow_factory,
        CloseTransferHandler(),
        CloseTransferCommand(transfer_doc_id=transfer_doc_id),
    )
