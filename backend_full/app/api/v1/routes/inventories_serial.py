from typing import Callable

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps.auth import PermissionChecker
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.serial.inventories import (
    CloseInventoryCommand,
    CloseInventoryHandler,
    CreateInventoryCommand,
    CreateInventoryHandler,
    GetInventoryExpectedHandler,
    GetInventoryExpectedQuery,
    GetInventoryHandler,
    GetInventoryQuery,
    GetInventoryResultHandler,
    GetInventoryResultQuery,
    ListInventoriesHandler,
    ListInventoriesQuery,
    ScanInventoryCommand,
    ScanInventoryHandler,
    StartInventoryCommand,
    StartInventoryHandler,
)
from app.schemas import serial as schemas

router = APIRouter(prefix="/inventories", tags=["serial-inventories"])


@router.post("", response_model=schemas.InventoryDocOut)
def create_inventory(
    payload: schemas.InventoryCreate,
    user=Depends(PermissionChecker(["inventories.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт документ инвентаризации по локации."""
    return dispatch_command(
        uow_factory,
        CreateInventoryHandler(),
        CreateInventoryCommand(payload=payload, created_by_user_id=getattr(user, "id", None)),
    )


@router.get("", response_model=list[schemas.InventoryDocListOut])
def list_inventories(
    status: str | None = Query(default=None),
    location_id: int | None = Query(default=None),
    created_by_user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["inventories.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список документов инвентаризации с фильтрами."""
    return dispatch_query(
        uow_factory,
        ListInventoriesHandler(),
        ListInventoriesQuery(
            status=status,
            location_id=location_id,
            created_by_user_id=created_by_user_id,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/{inventory_doc_id}", response_model=schemas.InventoryDocDetailOut)
def get_inventory(
    inventory_doc_id: int,
    user=Depends(PermissionChecker(["inventories.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает сводную информацию по инвентаризации."""
    return dispatch_query(uow_factory, GetInventoryHandler(), GetInventoryQuery(inventory_doc_id=inventory_doc_id))


@router.get("/{inventory_doc_id}/expected", response_model=schemas.InventoryExpectedListOut)
def get_inventory_expected(
    inventory_doc_id: int,
    user=Depends(PermissionChecker(["inventories.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список ожидаемых к сканированию коробок и item."""
    return dispatch_query(
        uow_factory,
        GetInventoryExpectedHandler(),
        GetInventoryExpectedQuery(inventory_doc_id=inventory_doc_id),
    )


@router.get("/{inventory_doc_id}/result", response_model=schemas.InventoryResultOut)
def get_inventory_result(
    inventory_doc_id: int,
    user=Depends(PermissionChecker(["inventories.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает итог учтено/не учтено для закрытой инвентаризации."""
    return dispatch_query(
        uow_factory,
        GetInventoryResultHandler(),
        GetInventoryResultQuery(inventory_doc_id=inventory_doc_id),
    )


@router.post("/{inventory_doc_id}/start")
def start_inventory(
    inventory_doc_id: int,
    user=Depends(PermissionChecker(["inventories.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Формирует ожидаемый список item и переводит документ в counting."""
    return dispatch_command(
        uow_factory,
        StartInventoryHandler(),
        StartInventoryCommand(inventory_doc_id=inventory_doc_id),
    )


@router.post("/{inventory_doc_id}/scan")
def scan_inventory(
    inventory_doc_id: int,
    payload: schemas.InventoryScan,
    user=Depends(PermissionChecker(["inventories.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Обрабатывает скан item/коробки в документе инвентаризации."""
    return dispatch_command(
        uow_factory,
        ScanInventoryHandler(),
        ScanInventoryCommand(inventory_doc_id=inventory_doc_id, payload=payload),
    )


@router.post("/{inventory_doc_id}/close")
def close_inventory(
    inventory_doc_id: int,
    user=Depends(PermissionChecker(["inventories.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Закрывает инвентаризацию и списывает missing как lost."""
    return dispatch_command(
        uow_factory,
        CloseInventoryHandler(),
        CloseInventoryCommand(inventory_doc_id=inventory_doc_id),
    )
