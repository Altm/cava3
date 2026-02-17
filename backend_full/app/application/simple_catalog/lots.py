from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func

from app.application.common.uow import AbstractUnitOfWork
from app.models import models
from app.schemas import simple as schemas


@dataclass(frozen=True)
class ListLotsQuery:
    location_id: Optional[int]
    product_id: Optional[int]
    lot_id: Optional[int]
    include_empty: bool
    limit: int
    offset: int


@dataclass(frozen=True)
class GetLotQuery:
    lot_id: int


class ListLotsHandler:
    def handle(self, query: ListLotsQuery, uow: AbstractUnitOfWork) -> list[schemas.LotListOut]:
        db = uow.session
        rows = (
            db.query(
                models.StockLot.id.label("lot_id"),
                models.StockLot.product_id,
                models.Product.name.label("product_name"),
                models.StockLot.supplier_lot_number,
                models.StockLot.purchase_price,
                models.StockLot.received_at,
                models.ProductItem.location_id,
                models.Location.name.label("location_name"),
                models.Location.code.label("location_code"),
                func.count(models.ProductItem.id).label("in_stock_items"),
            )
            .join(models.Product, models.Product.id == models.StockLot.product_id)
            .join(models.ProductItem, models.ProductItem.lot_id == models.StockLot.id)
            .join(models.Location, models.Location.id == models.ProductItem.location_id)
            .filter(models.ProductItem.status == "in_stock")
            .group_by(
                models.StockLot.id,
                models.StockLot.product_id,
                models.Product.name,
                models.StockLot.supplier_lot_number,
                models.StockLot.purchase_price,
                models.StockLot.received_at,
                models.ProductItem.location_id,
                models.Location.name,
                models.Location.code,
            )
        )

        if query.location_id is not None:
            rows = rows.filter(models.ProductItem.location_id == query.location_id)
        if query.product_id is not None:
            rows = rows.filter(models.StockLot.product_id == query.product_id)
        if query.lot_id is not None:
            rows = rows.filter(models.StockLot.id == query.lot_id)
        if not query.include_empty:
            rows = rows.having(func.count(models.ProductItem.id) > 0)

        rows = (
            rows.order_by(models.StockLot.received_at.desc(), models.StockLot.id.desc())
            .offset(query.offset)
            .limit(query.limit)
            .all()
        )

        return [
            schemas.LotListOut(
                lot_id=row.lot_id,
                product_id=row.product_id,
                product_name=row.product_name,
                supplier_lot_number=row.supplier_lot_number,
                purchase_price=row.purchase_price,
                received_at=row.received_at,
                location_id=row.location_id,
                location_name=row.location_name,
                location_code=row.location_code,
                in_stock_items=int(row.in_stock_items or 0),
            )
            for row in rows
        ]


class GetLotHandler:
    def handle(self, query: GetLotQuery, uow: AbstractUnitOfWork) -> schemas.LotDetailOut:
        db = uow.session
        lot_row = (
            db.query(
                models.StockLot.id.label("lot_id"),
                models.StockLot.product_id,
                models.Product.name.label("product_name"),
                models.StockLot.supplier_lot_number,
                models.StockLot.purchase_price,
                models.StockLot.received_at,
                models.StockLot.receipt_id,
                models.Receipt.status.label("receipt_status"),
            )
            .join(models.Product, models.Product.id == models.StockLot.product_id)
            .join(models.Receipt, models.Receipt.id == models.StockLot.receipt_id)
            .filter(models.StockLot.id == query.lot_id)
            .first()
        )
        if not lot_row:
            raise HTTPException(status_code=404, detail="Lot not found")

        items_rows = (
            db.query(
                models.ProductItem.id.label("product_item_id"),
                models.ProductItem.qr_code.label("product_item_qr_code"),
                models.ProductItem.status,
                models.ProductItem.location_id,
                models.Location.name.label("location_name"),
                models.Location.code.label("location_code"),
                models.ProductItem.box_id,
                models.Box.qr_code.label("box_qr_code"),
                models.ProductItem.created_at,
                models.ProductItem.updated_at,
            )
            .join(models.Location, models.Location.id == models.ProductItem.location_id)
            .outerjoin(models.Box, models.Box.id == models.ProductItem.box_id)
            .filter(models.ProductItem.lot_id == query.lot_id)
            .order_by(models.ProductItem.id.asc())
            .all()
        )
        in_stock_items = sum(1 for row in items_rows if row.status == "in_stock")

        return schemas.LotDetailOut(
            lot_id=lot_row.lot_id,
            product_id=lot_row.product_id,
            product_name=lot_row.product_name,
            supplier_lot_number=lot_row.supplier_lot_number,
            purchase_price=lot_row.purchase_price,
            received_at=lot_row.received_at,
            receipt_id=lot_row.receipt_id,
            receipt_status=lot_row.receipt_status,
            total_items=len(items_rows),
            in_stock_items=in_stock_items,
            items=[
                schemas.LotItemOut(
                    product_item_id=row.product_item_id,
                    product_item_qr_code=row.product_item_qr_code,
                    status=row.status,
                    location_id=row.location_id,
                    location_name=row.location_name,
                    location_code=row.location_code,
                    box_id=row.box_id,
                    box_qr_code=row.box_qr_code,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in items_rows
            ],
        )
