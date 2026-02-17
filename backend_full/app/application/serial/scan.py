from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import Box, Location, Product, ProductItem, Stock, TransferDoc, TransferItem, TransferLine
from app.schemas import serial as schemas
from app.services.serial_qr import parse_qr


@dataclass(frozen=True)
class ListProductItemsQuery:
    status: Optional[str]
    location_id: Optional[int]
    product_id: Optional[int]
    lot_id: Optional[int]
    box_id: Optional[int]
    reserved_transfer_doc_id: Optional[int]
    limit: int
    offset: int


@dataclass(frozen=True)
class GetProductItemHistoryQuery:
    product_item_id: int


@dataclass(frozen=True)
class ScanQrCommand:
    qr_code: str


class ListProductItemsHandler:
    def handle(self, query: ListProductItemsQuery, uow: AbstractUnitOfWork) -> list[schemas.ProductItemListOut]:
        db = uow.session
        query_builder = db.query(ProductItem)
        if query.status:
            query_builder = query_builder.filter(ProductItem.status == query.status)
        if query.location_id is not None:
            query_builder = query_builder.filter(ProductItem.location_id == query.location_id)
        if query.product_id is not None:
            query_builder = query_builder.filter(ProductItem.product_id == query.product_id)
        if query.lot_id is not None:
            query_builder = query_builder.filter(ProductItem.lot_id == query.lot_id)
        if query.box_id is not None:
            query_builder = query_builder.filter(ProductItem.box_id == query.box_id)
        if query.reserved_transfer_doc_id is not None:
            query_builder = query_builder.filter(ProductItem.reserved_transfer_doc_id == query.reserved_transfer_doc_id)
        query_builder = query_builder.order_by(ProductItem.id.desc()).offset(query.offset).limit(query.limit)
        return [schemas.ProductItemListOut.model_validate(row) for row in query_builder.all()]


class GetProductItemHistoryHandler:
    def handle(self, query: GetProductItemHistoryQuery, uow: AbstractUnitOfWork) -> schemas.ProductItemHistoryOut:
        db = uow.session
        item = db.query(ProductItem).filter(ProductItem.id == query.product_item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Product item not found")

        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        current_base_cost = Decimal(str(product.base_cost)) if product.base_cost is not None else Decimal("0")
        summary = schemas.ProductItemHistorySummaryOut(
            product_item_id=item.id,
            product_item_qr_code=item.qr_code,
            product_item_status=item.status,
            product_item_location_id=item.location_id,
            product_id=product.id,
            product_name=product.name,
            product_sku=product.sku,
            lot_id=item.lot_id,
            current_base_cost=current_base_cost,
            item_purchase_amount=current_base_cost,
        )

        stock_rows = (
            db.query(Stock.location_id, Location.name, Stock.quantity)
            .join(Location, Location.id == Stock.location_id)
            .filter(Stock.product_id == item.product_id)
            .order_by(Stock.location_id.asc())
            .all()
        )
        stock_balances = [
            schemas.ProductStockBalanceOut(
                location_id=location_id,
                location_name=location_name,
                quantity=quantity,
            )
            for location_id, location_name, quantity in stock_rows
        ]

        transfer_rows = (
            db.query(
                TransferDoc.id.label("transfer_doc_id"),
                TransferDoc.from_location_id,
                TransferDoc.to_location_id,
                TransferDoc.status.label("transfer_status"),
                TransferDoc.created_at.label("transfer_created_at"),
                TransferItem.state.label("transfer_item_state"),
                TransferItem.picked_at.label("shipped_at"),
                TransferItem.received_at,
            )
            .join(TransferLine, TransferLine.transfer_doc_id == TransferDoc.id)
            .join(TransferItem, TransferItem.transfer_line_id == TransferLine.id)
            .filter(TransferItem.product_item_id == query.product_item_id)
            .order_by(TransferDoc.id.asc(), TransferItem.id.asc())
            .all()
        )
        transfers: list[schemas.ProductItemTransferHistoryOut] = []
        for row in transfer_rows:
            is_lost = bool(
                item.status == "lost"
                and item.lost_reason == "lost_in_transit"
                and item.lost_doc_type == "transfer"
                and item.lost_doc_id == row.transfer_doc_id
            ) or bool(row.transfer_status == "closed" and row.transfer_item_state == "picked" and row.received_at is None)
            transfers.append(
                schemas.ProductItemTransferHistoryOut(
                    transfer_doc_id=row.transfer_doc_id,
                    from_location_id=row.from_location_id,
                    to_location_id=row.to_location_id,
                    transfer_status=row.transfer_status,
                    transfer_item_state=row.transfer_item_state,
                    transfer_created_at=row.transfer_created_at,
                    shipped_at=row.shipped_at,
                    received_at=row.received_at,
                    is_lost=is_lost,
                )
            )

        return schemas.ProductItemHistoryOut(summary=summary, stock_balances=stock_balances, transfers=transfers)


class ScanQrHandler:
    def handle(self, command: ScanQrCommand, uow: AbstractUnitOfWork) -> schemas.ScanOut:
        db = uow.session
        parsed = parse_qr(command.qr_code)
        if parsed.kind == "ITM":
            item = db.query(ProductItem).filter(ProductItem.uuid == parsed.uuid).first()
            if not item:
                return schemas.ScanOut(kind="ITM", found=False, uuid=parsed.uuid)
            return schemas.ScanOut(
                kind="ITM",
                found=True,
                uuid=item.uuid,
                id=item.id,
                status=item.status,
                location_id=item.location_id,
                product_id=item.product_id,
                lot_id=item.lot_id,
                box_id=item.box_id,
                reserved_transfer_doc_id=item.reserved_transfer_doc_id,
            )

        box = db.query(Box).filter(Box.uuid == parsed.uuid).first()
        if not box:
            return schemas.ScanOut(kind="BOX", found=False, uuid=parsed.uuid)
        return schemas.ScanOut(
            kind="BOX",
            found=True,
            uuid=box.uuid,
            id=box.id,
            status=box.status,
            location_id=box.location_id,
            product_id=box.product_id,
            lot_id=box.lot_id,
            sealed=box.sealed,
        )
