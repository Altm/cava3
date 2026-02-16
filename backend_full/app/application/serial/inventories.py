from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import InventoryDoc, InventoryItem
from app.schemas import serial as schemas
from app.services.serial_inventories import InventoryService


@dataclass(frozen=True)
class CreateInventoryCommand:
    payload: schemas.InventoryCreate
    created_by_user_id: Optional[int]


@dataclass(frozen=True)
class ListInventoriesQuery:
    status: Optional[str]
    location_id: Optional[int]
    created_by_user_id: Optional[int]
    limit: int
    offset: int


@dataclass(frozen=True)
class GetInventoryQuery:
    inventory_doc_id: int


@dataclass(frozen=True)
class StartInventoryCommand:
    inventory_doc_id: int


@dataclass(frozen=True)
class ScanInventoryCommand:
    inventory_doc_id: int
    payload: schemas.InventoryScan


@dataclass(frozen=True)
class CloseInventoryCommand:
    inventory_doc_id: int


def _service(uow: AbstractUnitOfWork) -> InventoryService:
    return InventoryService(uow.session)


class CreateInventoryHandler:
    def handle(self, command: CreateInventoryCommand, uow: AbstractUnitOfWork) -> schemas.InventoryDocOut:
        doc = _service(uow).create(command.payload.location_id, created_by_user_id=command.created_by_user_id)
        return schemas.InventoryDocOut.model_validate(doc)


class ListInventoriesHandler:
    def handle(self, query: ListInventoriesQuery, uow: AbstractUnitOfWork) -> list[schemas.InventoryDocListOut]:
        db = uow.session
        query_builder = db.query(InventoryDoc)
        if query.status:
            query_builder = query_builder.filter(InventoryDoc.status == query.status)
        if query.location_id is not None:
            query_builder = query_builder.filter(InventoryDoc.location_id == query.location_id)
        if query.created_by_user_id is not None:
            query_builder = query_builder.filter(InventoryDoc.created_by_user_id == query.created_by_user_id)
        query_builder = query_builder.order_by(InventoryDoc.id.desc()).offset(query.offset).limit(query.limit)
        return [schemas.InventoryDocListOut.model_validate(row) for row in query_builder.all()]


class GetInventoryHandler:
    def handle(self, query: GetInventoryQuery, uow: AbstractUnitOfWork) -> schemas.InventoryDocDetailOut:
        db = uow.session
        doc = db.query(InventoryDoc).filter(InventoryDoc.id == query.inventory_doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Inventory doc not found")

        base_query = db.query(InventoryItem).filter(InventoryItem.inventory_doc_id == query.inventory_doc_id)
        expected_count = base_query.filter(InventoryItem.state == "expected").count()
        scanned_count = base_query.filter(InventoryItem.state == "scanned").count()
        missing_count = base_query.filter(InventoryItem.state == "missing").count()
        unexpected_count = base_query.filter(InventoryItem.state == "unexpected").count()

        return schemas.InventoryDocDetailOut(
            id=doc.id,
            location_id=doc.location_id,
            status=doc.status,
            created_by_user_id=doc.created_by_user_id,
            closed_at=doc.closed_at,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            expected_count=expected_count,
            scanned_count=scanned_count,
            missing_count=missing_count,
            unexpected_count=unexpected_count,
        )


class StartInventoryHandler:
    def handle(self, command: StartInventoryCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow).start(command.inventory_doc_id)


class ScanInventoryHandler:
    def handle(self, command: ScanInventoryCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow).scan(command.inventory_doc_id, command.payload.qr_code)


class CloseInventoryHandler:
    def handle(self, command: CloseInventoryCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow).close(command.inventory_doc_id)
