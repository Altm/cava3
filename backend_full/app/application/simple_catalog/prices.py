from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import aliased

from app.application.common.uow import AbstractUnitOfWork
from app.config import get_settings
from app.models import models
from app.schemas import simple as schemas
from app.services.pricing_calculators import list_available_calculators, run_calculator


def _money(value: Decimal | str | float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ListPriceCalculatorsQuery:
    pass


@dataclass(frozen=True)
class CreatePriceRevisionCommand:
    payload: schemas.PriceRevisionCreate
    created_by_user_id: Optional[int]


@dataclass(frozen=True)
class ListPriceRevisionsQuery:
    location_id: Optional[int]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    limit: int
    offset: int


@dataclass(frozen=True)
class GetPriceRevisionQuery:
    revision_id: int


@dataclass(frozen=True)
class GetCurrentPriceQuery:
    location_id: int


class ListPriceCalculatorsHandler:
    def handle(self, query: ListPriceCalculatorsQuery, uow: AbstractUnitOfWork) -> list[schemas.PriceCalculatorOut]:
        rows = list_available_calculators()
        return [
            schemas.PriceCalculatorOut(
                file=row.file,
                class_name=row.class_name,
                description=row.description,
            )
            for row in rows
        ]


class CreatePriceRevisionHandler:
    def handle(self, command: CreatePriceRevisionCommand, uow: AbstractUnitOfWork) -> schemas.PriceRevisionDetailOut:
        db = uow.session
        payload = command.payload
        settings = get_settings()

        location = db.query(models.Location).filter(models.Location.id == payload.location_id).first()
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")

        mode = payload.mode
        if mode == "percent" and payload.percent_delta is None:
            raise HTTPException(status_code=400, detail="percent_delta is required for percent mode")
        if mode == "fixed" and payload.amount_delta is None:
            raise HTTPException(status_code=400, detail="amount_delta is required for fixed mode")
        if mode == "calculator" and (not payload.calculator_file or not payload.calculator_class):
            raise HTTPException(status_code=400, detail="calculator_file and calculator_class are required for calculator mode")

        base_currency = (payload.currency or settings.default_currency or "USD").upper()
        calculator_params = payload.calculator_params or {}

        products = (
            db.query(models.Product)
            .join(
                models.Stock,
                (models.Stock.product_id == models.Product.id) & (models.Stock.location_id == location.id),
            )
            .filter(
                models.Product.is_active == True,  # noqa: E712
                models.Stock.quantity > 0,
            )
            .all()
        )
        products_by_id = {product.id: product for product in products}
        if not products_by_id:
            raise HTTPException(status_code=409, detail="No in-stock products to recalculate for this location")

        existing_rows = (
            db.query(models.PriceList)
            .filter(models.PriceList.location_id == location.id)
            .all()
        )
        current_map: dict[tuple[int, int], models.PriceList] = {
            (row.product_id, row.unit_id): row
            for row in existing_rows
            if row.product_id in products_by_id
        }

        line_keys = set(current_map.keys())
        for product in products:
            line_keys.add((product.id, product.base_unit_id))

        revision = models.PriceListRevision(
            location_id=location.id,
            name=payload.name,
            mode=mode,
            percent_delta=payload.percent_delta,
            amount_delta=payload.amount_delta,
            currency=base_currency,
            calculator_file=payload.calculator_file,
            calculator_class=payload.calculator_class,
            calculator_params=calculator_params,
            created_by_user_id=command.created_by_user_id,
        )
        db.add(revision)
        db.flush()

        generated_items: list[schemas.PriceRevisionItemOut] = []
        purchase_metrics_cache: dict[int, tuple[Optional[Decimal], list[schemas.PriceItemLotOut]]] = {}
        for product_id, unit_id in sorted(line_keys):
            product = products_by_id.get(product_id)
            if not product:
                continue
            unit = db.query(models.Unit).filter(models.Unit.id == unit_id).first()
            if not unit:
                continue
            current_row = current_map.get((product_id, unit_id))
            previous_amount = _money(current_row.amount) if current_row else _money(product.base_cost or Decimal("0"))
            line_currency = (current_row.currency if current_row else base_currency).upper()

            if mode == "percent":
                percent = Decimal(str(payload.percent_delta or 0))
                next_amount = previous_amount * (Decimal("1") + (percent / Decimal("100")))
            elif mode == "fixed":
                delta = Decimal(str(payload.amount_delta or 0))
                next_amount = previous_amount + delta
            else:
                next_amount = run_calculator(
                    file_name=str(payload.calculator_file),
                    class_name=str(payload.calculator_class),
                    current_amount=previous_amount,
                    params=calculator_params,
                    context={
                        "location_id": location.id,
                        "product_id": product.id,
                        "product_name": product.name,
                        "unit_id": unit.id,
                        "unit_code": unit.code,
                        "currency": line_currency,
                    },
                )
            next_amount = _money(next_amount)
            if next_amount < Decimal("0.00"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Negative price is not allowed for product_id={product.id}, unit_id={unit.id}",
                )

            db.add(
                models.PriceListRevisionItem(
                    revision_id=revision.id,
                    product_id=product.id,
                    unit_id=unit.id,
                    currency=line_currency,
                    previous_amount=previous_amount,
                    amount=next_amount,
                )
            )

            if current_row:
                current_row.amount = next_amount
                current_row.currency = line_currency
            else:
                db.add(
                    models.PriceList(
                        location_id=location.id,
                        product_id=product.id,
                        unit_id=unit.id,
                        currency=line_currency,
                        amount=next_amount,
                    )
                )

            if product.id not in purchase_metrics_cache:
                purchase_metrics_cache[product.id] = _purchase_metrics(
                    db=db,
                    location_id=location.id,
                    product_id=product.id,
                    fallback_base_price=_money(product.base_cost or Decimal("0")),
                )
            avg_purchase_cost, lots = purchase_metrics_cache[product.id]
            generated_items.append(
                schemas.PriceRevisionItemOut(
                    product_id=product.id,
                    product_name=product.name,
                    unit_id=unit.id,
                    unit_code=unit.code,
                    currency=line_currency,
                    amount=next_amount,
                    previous_amount=previous_amount,
                    base_price=_money(product.base_cost or Decimal("0")),
                    average_purchase_cost=avg_purchase_cost,
                    lots=lots,
                )
            )

        if not generated_items:
            raise HTTPException(status_code=409, detail="No price lines generated")

        db.flush()
        return schemas.PriceRevisionDetailOut(
            id=revision.id,
            location_id=location.id,
            location_name=location.name,
            name=revision.name,
            mode=revision.mode,
            currency=revision.currency,
            percent_delta=revision.percent_delta,
            amount_delta=revision.amount_delta,
            calculator_file=revision.calculator_file,
            calculator_class=revision.calculator_class,
            calculator_params=revision.calculator_params or {},
            created_by_user_id=revision.created_by_user_id,
            created_at=revision.created_at,
            items=generated_items,
        )


class ListPriceRevisionsHandler:
    def handle(self, query: ListPriceRevisionsQuery, uow: AbstractUnitOfWork) -> list[schemas.PriceRevisionListOut]:
        db = uow.session
        next_revision = aliased(models.PriceListRevision)
        next_created_subq = (
            db.query(func.min(next_revision.created_at))
            .filter(
                next_revision.location_id == models.PriceListRevision.location_id,
                next_revision.id > models.PriceListRevision.id,
            )
            .correlate(models.PriceListRevision)
            .scalar_subquery()
        )
        items_count_subq = (
            db.query(
                models.PriceListRevisionItem.revision_id.label("revision_id"),
                func.count(models.PriceListRevisionItem.id).label("items_count"),
            )
            .group_by(models.PriceListRevisionItem.revision_id)
            .subquery()
        )

        query_builder = (
            db.query(
                models.PriceListRevision,
                models.Location.name.label("location_name"),
                func.coalesce(items_count_subq.c.items_count, 0).label("items_count"),
                next_created_subq.label("effective_to"),
            )
            .join(models.Location, models.Location.id == models.PriceListRevision.location_id)
            .outerjoin(items_count_subq, items_count_subq.c.revision_id == models.PriceListRevision.id)
        )
        if query.location_id is not None:
            query_builder = query_builder.filter(models.PriceListRevision.location_id == query.location_id)
        if query.date_from is not None:
            query_builder = query_builder.filter(models.PriceListRevision.created_at >= query.date_from)
        if query.date_to is not None:
            query_builder = query_builder.filter(models.PriceListRevision.created_at <= query.date_to)

        rows = (
            query_builder
            .order_by(models.PriceListRevision.id.desc())
            .offset(query.offset)
            .limit(query.limit)
            .all()
        )

        return [
            schemas.PriceRevisionListOut(
                id=revision.id,
                location_id=revision.location_id,
                location_name=location_name,
                name=revision.name,
                mode=revision.mode,
                currency=revision.currency,
                percent_delta=revision.percent_delta,
                amount_delta=revision.amount_delta,
                calculator_file=revision.calculator_file,
                calculator_class=revision.calculator_class,
                created_by_user_id=revision.created_by_user_id,
                created_at=revision.created_at,
                effective_from=revision.created_at,
                effective_to=effective_to,
                items_count=int(items_count),
            )
            for revision, location_name, items_count, effective_to in rows
        ]


class GetPriceRevisionHandler:
    def handle(self, query: GetPriceRevisionQuery, uow: AbstractUnitOfWork) -> schemas.PriceRevisionDetailOut:
        db = uow.session
        revision_row = (
            db.query(models.PriceListRevision, models.Location.name.label("location_name"))
            .join(models.Location, models.Location.id == models.PriceListRevision.location_id)
            .filter(models.PriceListRevision.id == query.revision_id)
            .first()
        )
        if not revision_row:
            raise HTTPException(status_code=404, detail="Price revision not found")
        revision, location_name = revision_row

        lines = _load_revision_lines(db, revision.id)
        return schemas.PriceRevisionDetailOut(
            id=revision.id,
            location_id=revision.location_id,
            location_name=location_name,
            name=revision.name,
            mode=revision.mode,
            currency=revision.currency,
            percent_delta=revision.percent_delta,
            amount_delta=revision.amount_delta,
            calculator_file=revision.calculator_file,
            calculator_class=revision.calculator_class,
            calculator_params=revision.calculator_params or {},
            created_by_user_id=revision.created_by_user_id,
            created_at=revision.created_at,
            items=lines,
        )


class GetCurrentPriceHandler:
    def handle(self, query: GetCurrentPriceQuery, uow: AbstractUnitOfWork) -> schemas.PriceCurrentOut:
        db = uow.session
        location = db.query(models.Location).filter(models.Location.id == query.location_id).first()
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")

        revision = (
            db.query(models.PriceListRevision)
            .filter(models.PriceListRevision.location_id == location.id)
            .order_by(models.PriceListRevision.id.desc())
            .first()
        )
        rows = (
            db.query(
                models.PriceList.product_id,
                models.Product.name.label("product_name"),
                models.Product.base_cost.label("base_price"),
                models.PriceList.unit_id,
                models.Unit.code.label("unit_code"),
                models.PriceList.currency,
                models.PriceList.amount,
            )
            .join(models.Product, models.Product.id == models.PriceList.product_id)
            .join(models.Unit, models.Unit.id == models.PriceList.unit_id)
            .join(
                models.Stock,
                (models.Stock.product_id == models.PriceList.product_id)
                & (models.Stock.location_id == models.PriceList.location_id),
            )
            .filter(models.PriceList.location_id == location.id)
            .filter(models.Stock.quantity > 0)
            .order_by(models.PriceList.product_id.asc(), models.PriceList.unit_id.asc())
            .all()
        )
        metrics_cache: dict[int, tuple[Optional[Decimal], list[schemas.PriceItemLotOut]]] = {}
        items: list[schemas.PriceRevisionItemOut] = []
        for row in rows:
            if row.product_id not in metrics_cache:
                metrics_cache[row.product_id] = _purchase_metrics(
                    db=db,
                    location_id=location.id,
                    product_id=row.product_id,
                    fallback_base_price=_money(row.base_price or Decimal("0")),
                )
            avg_purchase_cost, lots = metrics_cache[row.product_id]
            items.append(
                schemas.PriceRevisionItemOut(
                    product_id=row.product_id,
                    product_name=row.product_name,
                    unit_id=row.unit_id,
                    unit_code=row.unit_code,
                    currency=row.currency,
                    amount=_money(row.amount),
                    previous_amount=None,
                    base_price=_money(row.base_price or Decimal("0")),
                    average_purchase_cost=avg_purchase_cost,
                    lots=lots,
                )
            )
        return schemas.PriceCurrentOut(
            location_id=location.id,
            location_name=location.name,
            revision_id=revision.id if revision else None,
            revision_name=revision.name if revision else None,
            revision_created_at=revision.created_at if revision else None,
            items=items,
        )


def _load_revision_lines(db, revision_id: int) -> list[schemas.PriceRevisionItemOut]:
    rows = (
        db.query(
            models.PriceListRevisionItem.product_id,
            models.Product.name.label("product_name"),
            models.Product.base_cost.label("base_price"),
            models.PriceListRevisionItem.unit_id,
            models.Unit.code.label("unit_code"),
            models.PriceListRevisionItem.currency,
            models.PriceListRevisionItem.amount,
            models.PriceListRevisionItem.previous_amount,
        )
        .join(models.Product, models.Product.id == models.PriceListRevisionItem.product_id)
        .join(models.Unit, models.Unit.id == models.PriceListRevisionItem.unit_id)
        .filter(models.PriceListRevisionItem.revision_id == revision_id)
        .order_by(models.PriceListRevisionItem.product_id.asc(), models.PriceListRevisionItem.unit_id.asc())
        .all()
    )
    return [
        schemas.PriceRevisionItemOut(
            product_id=row.product_id,
            product_name=row.product_name,
            unit_id=row.unit_id,
            unit_code=row.unit_code,
            currency=row.currency,
            amount=_money(row.amount),
            previous_amount=_money(row.previous_amount) if row.previous_amount is not None else None,
            base_price=_money(row.base_price or Decimal("0")),
            average_purchase_cost=None,
            lots=[],
        )
        for row in rows
    ]


def _purchase_metrics(
    *,
    db,
    location_id: int,
    product_id: int,
    fallback_base_price: Decimal,
) -> tuple[Optional[Decimal], list[schemas.PriceItemLotOut]]:
    rows = (
        db.query(
            models.StockLot.id.label("lot_id"),
            models.StockLot.supplier_lot_number,
            models.StockLot.received_at,
            models.StockLot.purchase_price,
            func.count(models.ProductItem.id).label("items_count"),
        )
        .join(models.ProductItem, models.ProductItem.lot_id == models.StockLot.id)
        .filter(
            models.ProductItem.product_id == product_id,
            models.ProductItem.location_id == location_id,
            models.ProductItem.status == "in_stock",
        )
        .group_by(
            models.StockLot.id,
            models.StockLot.supplier_lot_number,
            models.StockLot.received_at,
            models.StockLot.purchase_price,
        )
        .order_by(models.StockLot.received_at.asc(), models.StockLot.id.asc())
        .all()
    )

    lots: list[schemas.PriceItemLotOut] = []
    total_items = 0
    weighted_sum = Decimal("0")
    for row in rows:
        lot_price = _money(row.purchase_price) if row.purchase_price is not None else fallback_base_price
        items_count = int(row.items_count or 0)
        if items_count > 0:
            total_items += items_count
            weighted_sum += (lot_price * Decimal(items_count))
        lots.append(
            schemas.PriceItemLotOut(
                lot_id=row.lot_id,
                supplier_lot_number=row.supplier_lot_number,
                received_at=row.received_at,
                purchase_price=lot_price,
                in_stock_items=items_count,
            )
        )
    average = None
    if total_items > 0:
        average = _money(weighted_sum / Decimal(total_items))
    elif fallback_base_price is not None:
        average = fallback_base_price

    return average, lots
