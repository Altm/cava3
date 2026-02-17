from typing import Callable

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps.auth import PermissionChecker
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.serial.boxes import (
    AddItemToBoxCommand,
    AddItemToBoxHandler,
    BoxLabelsHandler,
    BoxLabelsQuery,
    CreateBoxCommand,
    CreateBoxHandler,
    GetBoxHandler,
    GetBoxQuery,
    ListBoxesHandler,
    ListBoxesQuery,
    OpenBoxCommand,
    OpenBoxHandler,
    SealBoxCommand,
    SealBoxHandler,
)
from app.schemas import serial as schemas

router = APIRouter(prefix="/boxes", tags=["serial-boxes"])


@router.post("", response_model=schemas.BoxOut)
def create_box(
    payload: schemas.BoxCreate,
    user=Depends(PermissionChecker(["boxes.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт коробку для выбранного товара/партии/локации."""
    return dispatch_command(uow_factory, CreateBoxHandler(), CreateBoxCommand(payload=payload))


@router.get("", response_model=list[schemas.BoxListOut])
def list_boxes(
    status: str | None = Query(default=None),
    sealed: bool | None = Query(default=None),
    location_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    lot_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["boxes.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список коробок с фильтрами."""
    return dispatch_query(
        uow_factory,
        ListBoxesHandler(),
        ListBoxesQuery(
            status=status,
            sealed=sealed,
            location_id=location_id,
            product_id=product_id,
            lot_id=lot_id,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/{box_id}", response_model=schemas.BoxOut)
def get_box(
    box_id: int,
    user=Depends(PermissionChecker(["boxes.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает коробку по внутреннему id."""
    return dispatch_query(uow_factory, GetBoxHandler(), GetBoxQuery(box_id=box_id))


@router.post("/{box_id}/open", response_model=schemas.BoxOut)
def open_box(
    box_id: int,
    user=Depends(PermissionChecker(["boxes.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Открывает коробку (sealed=false) для частичных операций."""
    return dispatch_command(uow_factory, OpenBoxHandler(), OpenBoxCommand(box_id=box_id))


@router.post("/{box_id}/seal", response_model=schemas.BoxOut)
def seal_box(
    box_id: int,
    user=Depends(PermissionChecker(["boxes.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Закрывает коробку (sealed=true)."""
    return dispatch_command(uow_factory, SealBoxHandler(), SealBoxCommand(box_id=box_id))


@router.post("/{box_id}/add-item")
def add_item_to_box(
    box_id: int,
    payload: schemas.BoxAddItem,
    user=Depends(PermissionChecker(["boxes.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Добавляет item в коробку по QR коду единицы."""
    return dispatch_command(
        uow_factory,
        AddItemToBoxHandler(),
        AddItemToBoxCommand(box_id=box_id, payload=payload),
    )


@router.get("/{box_id}/labels", response_model=schemas.LabelsOut)
def box_labels(
    box_id: int,
    user=Depends(PermissionChecker(["boxes.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список QR-этикеток коробки для печати."""
    return dispatch_query(uow_factory, BoxLabelsHandler(), BoxLabelsQuery(box_id=box_id))
