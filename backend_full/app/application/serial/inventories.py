from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import Box, InventoryDoc, InventoryItem, Product, ProductItem, Receipt, StockLot
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
class GetInventoryExpectedQuery:
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


class GetInventoryExpectedHandler:
    def handle(self, query: GetInventoryExpectedQuery, uow: AbstractUnitOfWork) -> schemas.InventoryExpectedListOut:
        db = uow.session
        doc = db.query(InventoryDoc).filter(InventoryDoc.id == query.inventory_doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Inventory doc not found")

        if doc.status == "draft":
            rows = (
                db.query(
                    ProductItem.id.label("product_item_id"),
                    ProductItem.qr_code.label("product_item_qr_code"),
                    ProductItem.product_id,
                    Product.name.label("product_name"),
                    ProductItem.box_id,
                    Box.qr_code.label("box_qr_code"),
                    Box.sealed.label("box_sealed"),
                    Box.quantity.label("box_quantity"),
                )
                .join(Product, Product.id == ProductItem.product_id)
                .join(StockLot, StockLot.id == ProductItem.lot_id)
                .join(Receipt, Receipt.id == StockLot.receipt_id)
                .outerjoin(Box, Box.id == ProductItem.box_id)
                .filter(
                    ProductItem.location_id == doc.location_id,
                    ProductItem.status == "in_stock",
                    Receipt.status == "posted",
                )
                .order_by(ProductItem.id.asc())
                .all()
            )
        else:
            rows = (
                db.query(
                    ProductItem.id.label("product_item_id"),
                    ProductItem.qr_code.label("product_item_qr_code"),
                    ProductItem.product_id,
                    Product.name.label("product_name"),
                    ProductItem.box_id,
                    Box.qr_code.label("box_qr_code"),
                    Box.sealed.label("box_sealed"),
                    Box.quantity.label("box_quantity"),
                )
                .join(InventoryItem, InventoryItem.product_item_id == ProductItem.id)
                .join(Product, Product.id == ProductItem.product_id)
                .outerjoin(Box, Box.id == ProductItem.box_id)
                .filter(
                    InventoryItem.inventory_doc_id == doc.id,
                    InventoryItem.state == "expected",
                )
                .order_by(ProductItem.id.asc())
                .all()
            )

        boxes_map: dict[int, schemas.InventoryExpectedBoxOut] = {}
        single_items: list[schemas.InventoryExpectedItemOut] = []

        for row in rows:
            item_row = schemas.InventoryExpectedItemOut(
                product_item_id=row.product_item_id,
                product_item_qr_code=row.product_item_qr_code,
                product_id=row.product_id,
                product_name=row.product_name,
                box_id=row.box_id,
                box_qr_code=row.box_qr_code,
                box_sealed=row.box_sealed,
            )
            if row.box_id is None:
                single_items.append(item_row)
                continue

            if row.box_id not in boxes_map:
                boxes_map[row.box_id] = schemas.InventoryExpectedBoxOut(
                    box_id=row.box_id,
                    box_qr_code=row.box_qr_code or "",
                    sealed=bool(row.box_sealed),
                    quantity=int(row.box_quantity or 0),
                    items_remaining=0,
                    items=[],
                )
            box_row = boxes_map[row.box_id]
            box_row.items_remaining += 1
            if not box_row.sealed:
                box_row.items.append(item_row)

        boxes = sorted(boxes_map.values(), key=lambda row: (0 if row.sealed else 1, row.box_id))
        single_items.sort(key=lambda row: row.product_item_id)

        return schemas.InventoryExpectedListOut(
            inventory_doc_id=doc.id,
            location_id=doc.location_id,
            status=doc.status,
            remaining_expected_count=len(rows),
            boxes=boxes,
            single_items=single_items,
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
