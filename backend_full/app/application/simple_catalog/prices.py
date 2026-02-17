from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func

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

            generated_items.append(
                schemas.PriceRevisionItemOut(
                    product_id=product.id,
                    product_name=product.name,
                    unit_id=unit.id,
                    unit_code=unit.code,
                    currency=line_currency,
                    amount=next_amount,
                    previous_amount=previous_amount,
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
            )
            .join(models.Location, models.Location.id == models.PriceListRevision.location_id)
            .outerjoin(items_count_subq, items_count_subq.c.revision_id == models.PriceListRevision.id)
        )
        if query.location_id is not None:
            query_builder = query_builder.filter(models.PriceListRevision.location_id == query.location_id)

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
                items_count=int(items_count),
            )
            for revision, location_name, items_count in rows
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
        if revision:
            lines = _load_revision_lines(db, revision.id)
            return schemas.PriceCurrentOut(
                location_id=location.id,
                location_name=location.name,
                revision_id=revision.id,
                revision_name=revision.name,
                revision_created_at=revision.created_at,
                items=lines,
            )

        rows = (
            db.query(
                models.PriceList.product_id,
                models.Product.name.label("product_name"),
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
        items = [
            schemas.PriceRevisionItemOut(
                product_id=row.product_id,
                product_name=row.product_name,
                unit_id=row.unit_id,
                unit_code=row.unit_code,
                currency=row.currency,
                amount=_money(row.amount),
                previous_amount=None,
            )
            for row in rows
        ]
        return schemas.PriceCurrentOut(
            location_id=location.id,
            location_name=location.name,
            revision_id=None,
            revision_name=None,
            revision_created_at=None,
            items=items,
        )


def _load_revision_lines(db, revision_id: int) -> list[schemas.PriceRevisionItemOut]:
    rows = (
        db.query(
            models.PriceListRevisionItem.product_id,
            models.Product.name.label("product_name"),
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
        )
        for row in rows
    ]
