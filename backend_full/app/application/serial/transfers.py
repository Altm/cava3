from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import Box, Product, ProductItem, TransferDoc, TransferItem, TransferLine
from app.schemas import serial as schemas
from app.services.serial_transfers import TransferService


@dataclass(frozen=True)
class CreateTransferCommand:
    payload: schemas.TransferCreate
    created_by_user_id: Optional[int]


@dataclass(frozen=True)
class ListTransfersQuery:
    status: Optional[str]
    from_location_id: Optional[int]
    to_location_id: Optional[int]
    product_id: Optional[int]
    created_by_user_id: Optional[int]
    limit: int
    offset: int


@dataclass(frozen=True)
class GetTransferQuery:
    transfer_doc_id: int


@dataclass(frozen=True)
class ListTransferItemsQuery:
    transfer_doc_id: int


@dataclass(frozen=True)
class PlanTransferCommand:
    transfer_doc_id: int
    payload: schemas.TransferPlan


@dataclass(frozen=True)
class RemoveTransferItemCommand:
    transfer_doc_id: int
    payload: schemas.TransferRemoveItem


@dataclass(frozen=True)
class ScanTransferCommand:
    transfer_doc_id: int
    payload: schemas.TransferScan


@dataclass(frozen=True)
class ShipTransferCommand:
    transfer_doc_id: int


@dataclass(frozen=True)
class CloseTransferCommand:
    transfer_doc_id: int


def _service(uow: AbstractUnitOfWork) -> TransferService:
    return TransferService(uow.session)


class CreateTransferHandler:
    def handle(self, command: CreateTransferCommand, uow: AbstractUnitOfWork) -> schemas.TransferDocOut:
        doc = _service(uow).create(
            command.payload.from_location_id,
            command.payload.to_location_id,
            created_by_user_id=command.created_by_user_id,
        )
        return schemas.TransferDocOut.model_validate(doc)


class ListTransfersHandler:
    def handle(self, query: ListTransfersQuery, uow: AbstractUnitOfWork) -> list[schemas.TransferDocListOut]:
        db = uow.session
        query_builder = db.query(TransferDoc)
        if query.product_id is not None:
            query_builder = query_builder.join(TransferLine, TransferLine.transfer_doc_id == TransferDoc.id).filter(
                TransferLine.product_id == query.product_id
            )
        if query.status:
            query_builder = query_builder.filter(TransferDoc.status == query.status)
        if query.from_location_id is not None:
            query_builder = query_builder.filter(TransferDoc.from_location_id == query.from_location_id)
        if query.to_location_id is not None:
            query_builder = query_builder.filter(TransferDoc.to_location_id == query.to_location_id)
        if query.created_by_user_id is not None:
            query_builder = query_builder.filter(TransferDoc.created_by_user_id == query.created_by_user_id)
        if query.product_id is not None:
            query_builder = query_builder.distinct()
        query_builder = query_builder.order_by(TransferDoc.id.desc()).offset(query.offset).limit(query.limit)
        return [schemas.TransferDocListOut.model_validate(row) for row in query_builder.all()]


class GetTransferHandler:
    def handle(self, query: GetTransferQuery, uow: AbstractUnitOfWork) -> schemas.TransferDocDetailOut:
        db = uow.session
        doc = db.query(TransferDoc).filter(TransferDoc.id == query.transfer_doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Transfer not found")

        base_query = (
            db.query(TransferItem)
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(TransferLine.transfer_doc_id == query.transfer_doc_id)
        )
        planned_count = base_query.filter(TransferItem.state == "planned").count()
        picked_count = base_query.filter(TransferItem.state == "picked").count()
        removed_count = base_query.filter(TransferItem.state == "removed").count()
        received_count = (
            db.query(func.count(TransferItem.id))
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(TransferLine.transfer_doc_id == query.transfer_doc_id, TransferItem.received_at.isnot(None))
            .scalar()
            or 0
        )
        line_rows = (
            db.query(
                TransferLine.id.label("transfer_line_id"),
                TransferLine.product_id,
                TransferLine.qty_base,
                TransferLine.pick_policy,
                Product.name.label("product_name"),
            )
            .join(Product, Product.id == TransferLine.product_id)
            .filter(TransferLine.transfer_doc_id == query.transfer_doc_id)
            .order_by(TransferLine.id.asc())
            .all()
        )
        qr_rows = (
            db.query(
                TransferItem.transfer_line_id,
                ProductItem.qr_code,
                Box.qr_code.label("box_qr_code"),
            )
            .join(ProductItem, ProductItem.id == TransferItem.product_item_id)
            .outerjoin(Box, Box.id == ProductItem.box_id)
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(TransferLine.transfer_doc_id == query.transfer_doc_id, TransferItem.state == "planned")
            .order_by(TransferItem.transfer_line_id.asc(), TransferItem.id.asc())
            .all()
        )
        planned_qr_codes_by_line: dict[int, list[str]] = {}
        planned_box_qr_codes_by_line: dict[int, list[str]] = {}
        for transfer_line_id, qr_code, box_qr_code in qr_rows:
            planned_qr_codes_by_line.setdefault(transfer_line_id, []).append(qr_code)
            if box_qr_code:
                box_list = planned_box_qr_codes_by_line.setdefault(transfer_line_id, [])
                if box_qr_code not in box_list:
                    box_list.append(box_qr_code)
        transfer_lines = [
            schemas.TransferPlanLineOut(
                transfer_line_id=row.transfer_line_id,
                product_id=row.product_id,
                product_name=row.product_name,
                qty_base=row.qty_base,
                pick_policy=row.pick_policy,
                planned_qr_codes=planned_qr_codes_by_line.get(row.transfer_line_id, []),
                planned_box_qr_codes=planned_box_qr_codes_by_line.get(row.transfer_line_id, []),
            )
            for row in line_rows
        ]

        return schemas.TransferDocDetailOut(
            id=doc.id,
            from_location_id=doc.from_location_id,
            to_location_id=doc.to_location_id,
            status=doc.status,
            created_by_user_id=doc.created_by_user_id,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            planned_count=planned_count,
            picked_count=picked_count,
            received_count=int(received_count),
            removed_count=removed_count,
            transfer_lines=transfer_lines,
        )


class ListTransferItemsHandler:
    def handle(self, query: ListTransferItemsQuery, uow: AbstractUnitOfWork) -> list[schemas.TransferItemMovementOut]:
        db = uow.session
        doc = db.query(TransferDoc).filter(TransferDoc.id == query.transfer_doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Transfer not found")

        rows = (
            db.query(
                TransferItem.id.label("transfer_item_id"),
                TransferItem.product_item_id,
                TransferItem.state.label("transfer_item_state"),
                TransferItem.picked_at.label("shipped_at"),
                TransferItem.received_at,
                ProductItem.qr_code.label("product_item_qr_code"),
                ProductItem.status.label("product_item_status"),
                ProductItem.lost_reason,
                ProductItem.lost_doc_type,
                ProductItem.lost_doc_id,
                TransferLine.product_id,
                Product.name.label("product_name"),
            )
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .join(ProductItem, ProductItem.id == TransferItem.product_item_id)
            .join(Product, Product.id == TransferLine.product_id)
            .filter(TransferLine.transfer_doc_id == query.transfer_doc_id)
            .order_by(TransferItem.id.asc())
            .all()
        )

        result: list[schemas.TransferItemMovementOut] = []
        for row in rows:
            is_closed_not_received = doc.status == "closed" and row.transfer_item_state == "picked" and row.received_at is None
            is_lost_item = (
                row.product_item_status == "lost"
                and row.lost_reason == "lost_in_transit"
                and row.lost_doc_type == "transfer"
                and row.lost_doc_id == doc.id
            )
            result.append(
                schemas.TransferItemMovementOut(
                    transfer_item_id=row.transfer_item_id,
                    product_item_id=row.product_item_id,
                    product_item_qr_code=row.product_item_qr_code,
                    product_id=row.product_id,
                    product_name=row.product_name,
                    transfer_item_state=row.transfer_item_state,
                    transfer_status=doc.status,
                    transfer_created_at=doc.created_at,
                    shipped_at=row.shipped_at,
                    received_at=row.received_at,
                    is_lost=bool(is_closed_not_received or is_lost_item),
                )
            )
        return result


class PlanTransferHandler:
    def handle(self, command: PlanTransferCommand, uow: AbstractUnitOfWork) -> schemas.TransferPlanOut:
        result = _service(uow).plan_fifo(command.transfer_doc_id, command.payload.product_id, command.payload.qty_base)
        return schemas.TransferPlanOut(
            transfer_doc_id=command.transfer_doc_id,
            transfer_line_id=result.transfer_line_id,
            planned_items=result.planned_items,
        )


class RemoveTransferItemHandler:
    def handle(self, command: RemoveTransferItemCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow).remove_planned_item(command.transfer_doc_id, command.payload.product_item_id)


class ScanTransferHandler:
    def handle(self, command: ScanTransferCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow).scan(command.transfer_doc_id, command.payload.qr_code, command.payload.mode)


class ShipTransferHandler:
    def handle(self, command: ShipTransferCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow).ship(command.transfer_doc_id)


class CloseTransferHandler:
    def handle(self, command: CloseTransferCommand, uow: AbstractUnitOfWork) -> dict:
        return _service(uow).close(command.transfer_doc_id)
