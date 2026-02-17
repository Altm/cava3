from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import Box
from app.schemas import serial as schemas
from app.services.serial_boxes import BoxService


@dataclass(frozen=True)
class CreateBoxCommand:
    payload: schemas.BoxCreate


@dataclass(frozen=True)
class ListBoxesQuery:
    status: Optional[str]
    sealed: Optional[bool]
    location_id: Optional[int]
    product_id: Optional[int]
    lot_id: Optional[int]
    limit: int
    offset: int


@dataclass(frozen=True)
class GetBoxQuery:
    box_id: int


@dataclass(frozen=True)
class OpenBoxCommand:
    box_id: int


@dataclass(frozen=True)
class SealBoxCommand:
    box_id: int


@dataclass(frozen=True)
class AddItemToBoxCommand:
    box_id: int
    payload: schemas.BoxAddItem


@dataclass(frozen=True)
class BoxLabelsQuery:
    box_id: int


def _service(uow: AbstractUnitOfWork) -> BoxService:
    return BoxService(uow.session)


class CreateBoxHandler:
    def handle(self, command: CreateBoxCommand, uow: AbstractUnitOfWork) -> schemas.BoxOut:
        payload = command.payload
        box = _service(uow).create(
            product_id=payload.product_id,
            lot_id=payload.lot_id,
            location_id=payload.location_id,
            sealed=payload.sealed,
        )
        return schemas.BoxOut.model_validate(box)


class ListBoxesHandler:
    def handle(self, query: ListBoxesQuery, uow: AbstractUnitOfWork) -> list[schemas.BoxListOut]:
        db = uow.session
        query_builder = db.query(Box)
        if query.status:
            query_builder = query_builder.filter(Box.status == query.status)
        if query.sealed is not None:
            query_builder = query_builder.filter(Box.sealed == query.sealed)
        if query.location_id is not None:
            query_builder = query_builder.filter(Box.location_id == query.location_id)
        if query.product_id is not None:
            query_builder = query_builder.filter(Box.product_id == query.product_id)
        if query.lot_id is not None:
            query_builder = query_builder.filter(Box.lot_id == query.lot_id)
        query_builder = query_builder.order_by(Box.id.desc()).offset(query.offset).limit(query.limit)
        return [schemas.BoxListOut.model_validate(row) for row in query_builder.all()]


class GetBoxHandler:
    def handle(self, query: GetBoxQuery, uow: AbstractUnitOfWork) -> schemas.BoxOut:
        box = uow.session.query(Box).filter(Box.id == query.box_id).first()
        if not box:
            raise HTTPException(status_code=404, detail="Box not found")
        return schemas.BoxOut.model_validate(box)


class OpenBoxHandler:
    def handle(self, command: OpenBoxCommand, uow: AbstractUnitOfWork) -> schemas.BoxOut:
        box = _service(uow).open_box(command.box_id)
        return schemas.BoxOut.model_validate(box)


class SealBoxHandler:
    def handle(self, command: SealBoxCommand, uow: AbstractUnitOfWork) -> schemas.BoxOut:
        box = _service(uow).seal_box(command.box_id)
        return schemas.BoxOut.model_validate(box)


class AddItemToBoxHandler:
    def handle(self, command: AddItemToBoxCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow).add_item_by_qr(command.box_id, command.payload.qr_code)


class BoxLabelsHandler:
    def handle(self, query: BoxLabelsQuery, uow: AbstractUnitOfWork) -> schemas.LabelsOut:
        labels = _service(uow).list_box_labels(query.box_id)
        return schemas.LabelsOut(labels=labels)
