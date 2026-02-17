from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import (
    Box,
    Location,
    Product,
    ProductItem,
    Receipt,
    SaleEvent,
    SaleLine,
    Stock,
    StockLot,
    TransferDoc,
    TransferItem,
    TransferLine,
)
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
class ListProductItemLogQuery:
    product_item_id: Optional[int]
    product_id: Optional[int]
    location_id: Optional[int]
    event_type: Optional[str]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    limit: int
    offset: int


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
                    event_type="transfer",
                    event_description=self._describe_transfer_event(row.transfer_status, row.transfer_item_state, is_lost),
                    doc_type="transfer",
                    doc_id=row.transfer_doc_id,
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

        receipt_row = (
            db.query(
                Receipt.id.label("receipt_id"),
                Receipt.status.label("receipt_status"),
                Receipt.to_location_id.label("to_location_id"),
                StockLot.received_at.label("received_at"),
            )
            .join(StockLot, StockLot.receipt_id == Receipt.id)
            .filter(StockLot.id == item.lot_id)
            .first()
        )
        if receipt_row:
            transfers.append(
                schemas.ProductItemTransferHistoryOut(
                    event_type="receipt",
                    event_description=f"Приёмка ({receipt_row.receipt_status})",
                    doc_type="receipt",
                    doc_id=receipt_row.receipt_id,
                    to_location_id=receipt_row.to_location_id,
                    transfer_status=receipt_row.receipt_status,
                    transfer_item_state="received",
                    transfer_created_at=receipt_row.received_at or item.created_at,
                )
            )

        sale_events = self._find_sales_for_item(db=db, item=item)
        if sale_events:
            for sale_event in sale_events:
                transfers.append(
                    schemas.ProductItemTransferHistoryOut(
                        event_type="sale",
                        event_description=f"Продажа ({sale_event.status})",
                        doc_type="sale",
                        doc_id=sale_event.id,
                        from_location_id=sale_event.location_id,
                        transfer_status=sale_event.status,
                        transfer_item_state="sold",
                        transfer_created_at=sale_event.confirmed_at or sale_event.created_at,
                    )
                )
        elif item.status == "sold":
            transfers.append(
                schemas.ProductItemTransferHistoryOut(
                    event_type="sale",
                    event_description="Продажа (без привязки к sale_event)",
                    doc_type="sale",
                    from_location_id=item.location_id,
                    transfer_status="confirmed",
                    transfer_item_state="sold",
                    transfer_created_at=item.updated_at,
                )
            )

        transfers.sort(key=lambda row: row.transfer_created_at)
        return schemas.ProductItemHistoryOut(summary=summary, stock_balances=stock_balances, transfers=transfers)

    @staticmethod
    def _describe_transfer_event(transfer_status: str, transfer_item_state: str, is_lost: bool) -> str:
        if is_lost:
            return "Утеряно при перемещении"
        if transfer_item_state == "planned":
            return "Запланировано к перемещению"
        if transfer_item_state == "picked":
            return "Отгружено со склада"
        if transfer_item_state == "removed":
            return "Удалено из плана перемещения"
        if transfer_status == "closed":
            return "Перемещение закрыто"
        return "Перемещение"

    @staticmethod
    def _find_sales_for_item(db, item: ProductItem) -> list[SaleEvent]:
        event_ids_query = (
            db.query(SaleLine.sale_event_id)
            .filter(SaleLine.product_id == item.product_id)
            .distinct()
        )
        candidates = (
            db.query(SaleEvent)
            .filter(SaleEvent.id.in_(event_ids_query))
            .order_by(SaleEvent.created_at.asc())
            .limit(5000)
            .all()
        )

        matched: list[SaleEvent] = []
        for sale_event in candidates:
            if GetProductItemHistoryHandler._sale_payload_contains_item_id(sale_event.payload, item.id):
                matched.append(sale_event)
        return matched

    @staticmethod
    def _sale_payload_contains_item_id(payload: dict | None, product_item_id: int) -> bool:
        if not isinstance(payload, dict):
            return False

        sales_entries: list[dict] = []
        sale_entry = payload.get("sale")
        if isinstance(sale_entry, dict):
            sales_entries.append(sale_entry)
        sales = payload.get("sales")
        if isinstance(sales, list):
            sales_entries.extend([entry for entry in sales if isinstance(entry, dict)])

        target_id = int(product_item_id)
        for sale in sales_entries:
            items = sale.get("items")
            if not isinstance(items, list):
                continue
            for row in items:
                if not isinstance(row, dict):
                    continue
                resolved = row.get("resolved_item_ids")
                if not isinstance(resolved, list):
                    continue
                for value in resolved:
                    try:
                        if int(value) == target_id:
                            return True
                    except (TypeError, ValueError):
                        continue
        return False


class ListProductItemLogHandler:
    def handle(self, query: ListProductItemLogQuery, uow: AbstractUnitOfWork) -> list[schemas.ProductItemLogOut]:
        db = uow.session
        query_window = max(500, (query.limit + query.offset) * 5)

        events: list[schemas.ProductItemLogOut] = []

        # Receipt events (initial appearance of item).
        receipt_query = (
            db.query(
                ProductItem.id.label("product_item_id"),
                ProductItem.qr_code.label("product_item_qr_code"),
                ProductItem.product_id,
                Product.name.label("product_name"),
                ProductItem.lot_id,
                StockLot.received_at.label("event_time"),
                Receipt.id.label("receipt_id"),
                Receipt.to_location_id.label("location_id"),
                Receipt.status.label("receipt_status"),
            )
            .join(Product, Product.id == ProductItem.product_id)
            .join(StockLot, StockLot.id == ProductItem.lot_id)
            .join(Receipt, Receipt.id == StockLot.receipt_id)
        )
        if query.product_item_id is not None:
            receipt_query = receipt_query.filter(ProductItem.id == query.product_item_id)
        if query.product_id is not None:
            receipt_query = receipt_query.filter(ProductItem.product_id == query.product_id)
        if query.location_id is not None:
            receipt_query = receipt_query.filter(Receipt.to_location_id == query.location_id)
        receipt_rows = receipt_query.order_by(StockLot.received_at.desc(), ProductItem.id.desc()).limit(query_window).all()
        for row in receipt_rows:
            events.append(
                schemas.ProductItemLogOut(
                    event_time=row.event_time,
                    event_type="receipt",
                    product_item_id=row.product_item_id,
                    product_item_qr_code=row.product_item_qr_code,
                    product_id=row.product_id,
                    product_name=row.product_name,
                    lot_id=row.lot_id,
                    location_id=row.location_id,
                    doc_type="receipt",
                    doc_id=row.receipt_id,
                    details=f"receipt_status={row.receipt_status}",
                )
            )

        # Transfer events.
        transfer_query = (
            db.query(
                TransferItem.id.label("transfer_item_id"),
                TransferItem.product_item_id,
                ProductItem.qr_code.label("product_item_qr_code"),
                ProductItem.product_id,
                Product.name.label("product_name"),
                ProductItem.lot_id,
                TransferDoc.id.label("transfer_doc_id"),
                TransferDoc.from_location_id,
                TransferDoc.to_location_id,
                TransferDoc.status.label("transfer_status"),
                TransferItem.state.label("transfer_item_state"),
                TransferItem.reserved_at,
                TransferItem.picked_at,
                TransferItem.received_at,
                TransferItem.updated_at,
            )
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .join(TransferDoc, TransferDoc.id == TransferLine.transfer_doc_id)
            .join(ProductItem, ProductItem.id == TransferItem.product_item_id)
            .join(Product, Product.id == ProductItem.product_id)
        )
        if query.product_item_id is not None:
            transfer_query = transfer_query.filter(TransferItem.product_item_id == query.product_item_id)
        if query.product_id is not None:
            transfer_query = transfer_query.filter(ProductItem.product_id == query.product_id)
        if query.location_id is not None:
            transfer_query = transfer_query.filter(
                (TransferDoc.from_location_id == query.location_id) | (TransferDoc.to_location_id == query.location_id)
            )
        transfer_rows = transfer_query.order_by(TransferItem.updated_at.desc(), TransferItem.id.desc()).limit(query_window).all()
        for row in transfer_rows:
            planned_time = row.reserved_at or row.updated_at
            if planned_time:
                events.append(
                    schemas.ProductItemLogOut(
                        event_time=planned_time,
                        event_type="transfer_planned",
                        product_item_id=row.product_item_id,
                        product_item_qr_code=row.product_item_qr_code,
                        product_id=row.product_id,
                        product_name=row.product_name,
                        lot_id=row.lot_id,
                        from_location_id=row.from_location_id,
                        to_location_id=row.to_location_id,
                        doc_type="transfer",
                        doc_id=row.transfer_doc_id,
                        details=f"transfer_status={row.transfer_status}",
                    )
                )
            if row.picked_at:
                events.append(
                    schemas.ProductItemLogOut(
                        event_time=row.picked_at,
                        event_type="transfer_picked",
                        product_item_id=row.product_item_id,
                        product_item_qr_code=row.product_item_qr_code,
                        product_id=row.product_id,
                        product_name=row.product_name,
                        lot_id=row.lot_id,
                        location_id=row.from_location_id,
                        from_location_id=row.from_location_id,
                        to_location_id=row.to_location_id,
                        doc_type="transfer",
                        doc_id=row.transfer_doc_id,
                        details=f"transfer_status={row.transfer_status}",
                    )
                )
            if row.received_at:
                events.append(
                    schemas.ProductItemLogOut(
                        event_time=row.received_at,
                        event_type="transfer_received",
                        product_item_id=row.product_item_id,
                        product_item_qr_code=row.product_item_qr_code,
                        product_id=row.product_id,
                        product_name=row.product_name,
                        lot_id=row.lot_id,
                        location_id=row.to_location_id,
                        from_location_id=row.from_location_id,
                        to_location_id=row.to_location_id,
                        doc_type="transfer",
                        doc_id=row.transfer_doc_id,
                        details=f"transfer_status={row.transfer_status}",
                    )
                )
            if row.transfer_item_state == "removed":
                events.append(
                    schemas.ProductItemLogOut(
                        event_time=row.updated_at,
                        event_type="transfer_removed",
                        product_item_id=row.product_item_id,
                        product_item_qr_code=row.product_item_qr_code,
                        product_id=row.product_id,
                        product_name=row.product_name,
                        lot_id=row.lot_id,
                        from_location_id=row.from_location_id,
                        to_location_id=row.to_location_id,
                        doc_type="transfer",
                        doc_id=row.transfer_doc_id,
                        details=f"transfer_status={row.transfer_status}",
                    )
                )

        # Terminal status events (sold/lost/damaged/voided).
        status_query = (
            db.query(
                ProductItem.id.label("product_item_id"),
                ProductItem.qr_code.label("product_item_qr_code"),
                ProductItem.product_id,
                Product.name.label("product_name"),
                ProductItem.lot_id,
                ProductItem.status,
                ProductItem.location_id,
                ProductItem.updated_at.label("event_time"),
                ProductItem.lost_doc_type,
                ProductItem.lost_doc_id,
                ProductItem.lost_reason,
            )
            .join(Product, Product.id == ProductItem.product_id)
            .filter(ProductItem.status.in_(["sold", "lost", "damaged", "voided"]))
        )
        if query.product_item_id is not None:
            status_query = status_query.filter(ProductItem.id == query.product_item_id)
        if query.product_id is not None:
            status_query = status_query.filter(ProductItem.product_id == query.product_id)
        if query.location_id is not None:
            status_query = status_query.filter(ProductItem.location_id == query.location_id)
        status_rows = status_query.order_by(ProductItem.updated_at.desc(), ProductItem.id.desc()).limit(query_window).all()
        for row in status_rows:
            events.append(
                schemas.ProductItemLogOut(
                    event_time=row.event_time,
                    event_type=f"status_{row.status}",
                    product_item_id=row.product_item_id,
                    product_item_qr_code=row.product_item_qr_code,
                    product_id=row.product_id,
                    product_name=row.product_name,
                    lot_id=row.lot_id,
                    location_id=row.location_id,
                    doc_type=row.lost_doc_type,
                    doc_id=row.lost_doc_id,
                    details=row.lost_reason,
                )
            )

        date_from = self._to_naive(query.date_from)
        date_to = self._to_naive(query.date_to)
        if date_from:
            events = [event for event in events if event.event_time >= date_from]
        if date_to:
            events = [event for event in events if event.event_time <= date_to]
        if query.event_type:
            events = [event for event in events if event.event_type == query.event_type]
        if query.location_id is not None:
            events = [
                event
                for event in events
                if event.location_id == query.location_id
                or event.from_location_id == query.location_id
                or event.to_location_id == query.location_id
            ]

        events.sort(key=lambda event: event.event_time, reverse=True)
        return events[query.offset : query.offset + query.limit]

    @staticmethod
    def _to_naive(value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)


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
