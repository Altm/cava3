from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import Box, Location, Product, ProductItem, Receipt, ReceiptLine, StockLot
from app.schemas import serial as schemas
from app.services.serial_receipts import ReceiptService


@dataclass(frozen=True)
class CreateReceiptCommand:
    payload: schemas.ReceiptCreate
    created_by_user_id: Optional[int]


@dataclass(frozen=True)
class ListReceiptsQuery:
    status: Optional[str]
    to_location_id: Optional[int]
    product_id: Optional[int]
    created_by_user_id: Optional[int]
    limit: int
    offset: int


@dataclass(frozen=True)
class GetReceiptQuery:
    receipt_id: int


@dataclass(frozen=True)
class GetReceiptLinesQuery:
    receipt_id: int


@dataclass(frozen=True)
class GetReceiptItemsQuery:
    receipt_id: int


@dataclass(frozen=True)
class AddReceiptLineCommand:
    receipt_id: int
    payload: schemas.ReceiptLineCreate


@dataclass(frozen=True)
class RemoveReceiptLineCommand:
    receipt_id: int
    line_id: int


@dataclass(frozen=True)
class GenerateReceiptCommand:
    receipt_id: int


@dataclass(frozen=True)
class PostReceiptCommand:
    receipt_id: int


@dataclass(frozen=True)
class VoidReceiptCommand:
    receipt_id: int


@dataclass(frozen=True)
class ReceiptItemLabelsQuery:
    receipt_id: int


@dataclass(frozen=True)
class ReceiptAutoBoxCommand:
    receipt_id: int
    payload: schemas.ReceiptAutoBoxRequest


def _service(db: Session) -> ReceiptService:
    return ReceiptService(db)


class CreateReceiptHandler:
    def handle(self, command: CreateReceiptCommand, uow: AbstractUnitOfWork) -> schemas.ReceiptOut:
        receipt = _service(uow.session).create(
            to_location_id=command.payload.to_location_id,
            created_by_user_id=command.created_by_user_id,
        )
        return schemas.ReceiptOut.model_validate(receipt)


class ListReceiptsHandler:
    def handle(self, query: ListReceiptsQuery, uow: AbstractUnitOfWork) -> list[schemas.ReceiptListOut]:
        db = uow.session
        query_builder = db.query(Receipt)
        if query.product_id is not None:
            query_builder = query_builder.join(ReceiptLine, ReceiptLine.receipt_id == Receipt.id).filter(
                ReceiptLine.product_id == query.product_id
            )
        if query.status:
            query_builder = query_builder.filter(Receipt.status == query.status)
        if query.to_location_id is not None:
            query_builder = query_builder.filter(Receipt.to_location_id == query.to_location_id)
        if query.created_by_user_id is not None:
            query_builder = query_builder.filter(Receipt.created_by_user_id == query.created_by_user_id)
        if query.product_id is not None:
            query_builder = query_builder.distinct()
        query_builder = query_builder.order_by(Receipt.id.desc()).offset(query.offset).limit(query.limit)
        return [schemas.ReceiptListOut.model_validate(row) for row in query_builder.all()]


class GetReceiptHandler:
    def handle(self, query: GetReceiptQuery, uow: AbstractUnitOfWork) -> schemas.ReceiptListOut:
        receipt = uow.session.query(Receipt).filter(Receipt.id == query.receipt_id).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        return schemas.ReceiptListOut.model_validate(receipt)


class GetReceiptLinesHandler:
    def handle(self, query: GetReceiptLinesQuery, uow: AbstractUnitOfWork) -> list[schemas.ReceiptLineOut]:
        db = uow.session
        exists = db.query(Receipt.id).filter(Receipt.id == query.receipt_id).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Receipt not found")
        rows = (
            db.query(ReceiptLine)
            .filter(ReceiptLine.receipt_id == query.receipt_id)
            .order_by(ReceiptLine.id.asc())
            .all()
        )
        return [schemas.ReceiptLineOut.model_validate(row) for row in rows]


class GetReceiptItemsHandler:
    def handle(self, query: GetReceiptItemsQuery, uow: AbstractUnitOfWork) -> list[schemas.ReceiptItemContentOut]:
        db = uow.session
        receipt = db.query(Receipt).filter(Receipt.id == query.receipt_id).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")

        rows = (
            db.query(
                ProductItem.id.label("product_item_id"),
                ProductItem.qr_code.label("product_item_qr_code"),
                ProductItem.status.label("product_item_status"),
                ProductItem.created_at.label("product_item_created_at"),
                ProductItem.updated_at.label("product_item_updated_at"),
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Product.sku.label("product_sku"),
                Product.base_cost.label("purchase_amount"),
                StockLot.id.label("lot_id"),
                StockLot.supplier_lot_number,
                StockLot.received_at.label("lot_received_at"),
                Box.id.label("box_id"),
                Box.qr_code.label("box_qr_code"),
                Location.id.label("location_id"),
                Location.name.label("location_name"),
                Location.code.label("location_code"),
            )
            .join(StockLot, StockLot.id == ProductItem.lot_id)
            .join(Product, Product.id == ProductItem.product_id)
            .join(Location, Location.id == ProductItem.location_id)
            .outerjoin(Box, Box.id == ProductItem.box_id)
            .filter(StockLot.receipt_id == query.receipt_id)
            .order_by(ProductItem.id.asc())
            .all()
        )
        return [
            schemas.ReceiptItemContentOut(
                product_item_id=row.product_item_id,
                product_item_qr_code=row.product_item_qr_code,
                product_item_status=row.product_item_status,
                product_item_created_at=row.product_item_created_at,
                product_item_updated_at=row.product_item_updated_at,
                product_id=row.product_id,
                product_name=row.product_name,
                product_sku=row.product_sku,
                purchase_amount=Decimal(str(row.purchase_amount)) if row.purchase_amount is not None else Decimal("0"),
                lot_id=row.lot_id,
                supplier_lot_number=row.supplier_lot_number,
                lot_received_at=row.lot_received_at,
                box_id=row.box_id,
                box_qr_code=row.box_qr_code,
                location_id=row.location_id,
                location_name=row.location_name,
                location_code=row.location_code,
                receipt_id=receipt.id,
                receipt_status=receipt.status,
                receipt_created_at=receipt.created_at,
            )
            for row in rows
        ]


class AddReceiptLineHandler:
    def handle(self, command: AddReceiptLineCommand, uow: AbstractUnitOfWork) -> schemas.ReceiptLineOut:
        line = _service(uow.session).add_line(
            receipt_id=command.receipt_id,
            product_id=command.payload.product_id,
            qty=Decimal(str(command.payload.qty)),
            unit_id=command.payload.unit_id,
            supplier_lot_number=command.payload.supplier_lot_number,
        )
        return schemas.ReceiptLineOut.model_validate(line)


class RemoveReceiptLineHandler:
    def handle(self, command: RemoveReceiptLineCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow.session).remove_line(receipt_id=command.receipt_id, line_id=command.line_id)


class GenerateReceiptHandler:
    def handle(self, command: GenerateReceiptCommand, uow: AbstractUnitOfWork) -> schemas.ReceiptGenerateOut:
        result = _service(uow.session).generate(command.receipt_id)
        return schemas.ReceiptGenerateOut(
            receipt_id=command.receipt_id,
            lots_created=result.lots_created,
            items_created=result.items_created,
        )


class PostReceiptHandler:
    def handle(self, command: PostReceiptCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow.session).post(command.receipt_id)


class VoidReceiptHandler:
    def handle(self, command: VoidReceiptCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow.session).void(command.receipt_id)


class ReceiptItemLabelsHandler:
    def handle(self, query: ReceiptItemLabelsQuery, uow: AbstractUnitOfWork) -> schemas.LabelsOut:
        labels = _service(uow.session).list_item_labels(query.receipt_id)
        return schemas.LabelsOut(labels=labels)


class ReceiptAutoBoxHandler:
    def handle(self, command: ReceiptAutoBoxCommand, uow: AbstractUnitOfWork) -> schemas.ReceiptAutoBoxOut:
        payload = command.payload
        result = _service(uow.session).auto_box(
            receipt_id=command.receipt_id,
            items_per_box=payload.items_per_box,
            max_boxes=payload.max_boxes,
            include_partial=payload.include_partial,
            seal_full_boxes=payload.seal_full_boxes,
            product_id=payload.product_id,
            lot_id=payload.lot_id,
        )
        return schemas.ReceiptAutoBoxOut(
            receipt_id=result.receipt_id,
            items_per_box=result.items_per_box,
            boxes_created=result.boxes_created,
            items_packed=result.items_packed,
            items_remaining_unboxed=result.items_remaining_unboxed,
            boxes=[
                schemas.ReceiptAutoBoxBoxOut(
                    id=box.id,
                    qr_code=box.qr_code,
                    product_id=box.product_id,
                    lot_id=box.lot_id,
                    location_id=box.location_id,
                    sealed=box.sealed,
                    packed_items=box.packed_items,
                )
                for box in result.boxes
            ],
        )
