from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models import models
from app.schemas import simple as schemas


@dataclass(frozen=True)
class ListProductTypesQuery:
    pass


@dataclass(frozen=True)
class GetProductTypeQuery:
    product_type_id: int


@dataclass(frozen=True)
class CreateProductTypeCommand:
    payload: schemas.ProductTypeCreate


@dataclass(frozen=True)
class UpdateProductTypeCommand:
    product_type_id: int
    payload: schemas.ProductTypeUpdate


@dataclass(frozen=True)
class DeleteProductTypeCommand:
    product_type_id: int


def _serialize_type_units(rows: list[models.ProductTypeUnit]) -> list[schemas.ProductTypeUnit]:
    return [
        schemas.ProductTypeUnit(
            id=row.id,
            product_type_id=row.product_type_id,
            unit_id=row.unit_id,
            ratio_to_base=row.ratio_to_base,
            discrete_step=row.discrete_step,
        )
        for row in sorted(
            rows,
            key=lambda unit: (unit.ratio_to_base, unit.unit_id),
            reverse=True,
        )
    ]


def _sync_type_units(
    db,
    *,
    product_type_id: int,
    payload_units: list[schemas.ProductTypeUnitCreate],
) -> None:
    desired_by_unit_id: dict[int, tuple[Decimal, Decimal | None]] = {}
    for row in payload_units:
        unit = db.get(models.Unit, row.unit_id)
        if not unit:
            raise HTTPException(status_code=400, detail=f"Unit not found: {row.unit_id}")
        desired_by_unit_id[row.unit_id] = (row.ratio_to_base, row.discrete_step)

    existing_rows = db.query(models.ProductTypeUnit).filter(models.ProductTypeUnit.product_type_id == product_type_id).all()
    existing_by_unit_id = {row.unit_id: row for row in existing_rows}

    for row in existing_rows:
        if row.unit_id not in desired_by_unit_id:
            db.delete(row)

    for unit_id, (ratio_to_base, discrete_step) in desired_by_unit_id.items():
        existing = existing_by_unit_id.get(unit_id)
        if existing:
            existing.ratio_to_base = ratio_to_base
            existing.discrete_step = discrete_step
            continue
        db.add(
            models.ProductTypeUnit(
                product_type_id=product_type_id,
                unit_id=unit_id,
                ratio_to_base=ratio_to_base,
                discrete_step=discrete_step,
            )
        )


class ListProductTypesHandler:
    def handle(self, query: ListProductTypesQuery, uow: AbstractUnitOfWork) -> List[schemas.ProductType]:
        db = uow.session
        types = db.query(models.ProductType).all()
        result: list[schemas.ProductType] = []
        for t in types:
            attrs = db.query(models.ProductAttribute).filter(models.ProductAttribute.product_type_id == t.id).all()
            type_units = db.query(models.ProductTypeUnit).filter(models.ProductTypeUnit.product_type_id == t.id).all()
            result.append(
                schemas.ProductType(
                    id=t.id,
                    name=t.name,
                    description=t.description,
                    is_composite=t.is_composite,
                    strict_units_by_type=t.strict_units_by_type,
                    attributes=attrs,
                    product_type_units=_serialize_type_units(type_units),
                )
            )
        return result


class GetProductTypeHandler:
    def handle(self, query: GetProductTypeQuery, uow: AbstractUnitOfWork) -> schemas.ProductType:
        db = uow.session
        t = db.get(models.ProductType, query.product_type_id)
        if not t:
            raise HTTPException(status_code=404, detail="Product type not found")
        attrs = db.query(models.ProductAttribute).filter(models.ProductAttribute.product_type_id == t.id).all()
        type_units = db.query(models.ProductTypeUnit).filter(models.ProductTypeUnit.product_type_id == t.id).all()
        return schemas.ProductType(
            id=t.id,
            name=t.name,
            description=t.description,
            is_composite=t.is_composite,
            strict_units_by_type=t.strict_units_by_type,
            attributes=attrs,
            product_type_units=_serialize_type_units(type_units),
        )


class CreateProductTypeHandler:
    def handle(self, command: CreateProductTypeCommand, uow: AbstractUnitOfWork) -> schemas.ProductType:
        db = uow.session
        payload = command.payload
        t = models.ProductType(
            name=payload.name,
            description=payload.description,
            is_composite=payload.is_composite,
            strict_units_by_type=payload.strict_units_by_type,
        )
        db.add(t)
        db.flush()

        if payload.attributes:
            for attr_data in payload.attributes:
                unit_id = None
                if attr_data.unit_id:
                    unit = db.get(models.Unit, attr_data.unit_id)
                    if unit:
                        unit_id = unit.id
                db.add(
                    models.ProductAttribute(
                        product_type_id=t.id,
                        name=attr_data.name,
                        code=attr_data.code,
                        data_type=attr_data.data_type,
                        unit_id=unit_id,
                        is_required=attr_data.is_required,
                        sort_order=attr_data.sort_order,
                    )
                )
        _sync_type_units(
            db,
            product_type_id=t.id,
            payload_units=payload.product_type_units or [],
        )
        db.flush()
        attrs = db.query(models.ProductAttribute).filter(models.ProductAttribute.product_type_id == t.id).all()
        type_units = db.query(models.ProductTypeUnit).filter(models.ProductTypeUnit.product_type_id == t.id).all()
        return schemas.ProductType(
            id=t.id,
            name=t.name,
            description=t.description,
            is_composite=t.is_composite,
            strict_units_by_type=t.strict_units_by_type,
            attributes=attrs,
            product_type_units=_serialize_type_units(type_units),
        )


class UpdateProductTypeHandler:
    def handle(self, command: UpdateProductTypeCommand, uow: AbstractUnitOfWork) -> schemas.ProductType:
        db = uow.session
        t = db.get(models.ProductType, command.product_type_id)
        if not t:
            raise HTTPException(status_code=404, detail="Product type not found")

        payload = command.payload
        t.name = payload.name
        t.description = payload.description
        t.is_composite = payload.is_composite
        t.strict_units_by_type = payload.strict_units_by_type

        attr_def_ids = db.query(models.ProductAttribute.id).filter(
            models.ProductAttribute.product_type_id == command.product_type_id
        ).all()
        if attr_def_ids:
            attr_def_id_list = [row[0] for row in attr_def_ids]
            db.query(models.ProductAttributeValue).filter(
                models.ProductAttributeValue.product_attribute_id.in_(attr_def_id_list)
            ).delete()

        db.query(models.ProductAttribute).filter(
            models.ProductAttribute.product_type_id == command.product_type_id
        ).delete()

        if payload.attributes:
            for attr_data in payload.attributes:
                unit_id = None
                if attr_data.unit_id:
                    unit = db.get(models.Unit, attr_data.unit_id)
                    if unit:
                        unit_id = unit.id
                db.add(
                    models.ProductAttribute(
                        product_type_id=command.product_type_id,
                        name=attr_data.name,
                        code=attr_data.code,
                        data_type=attr_data.data_type,
                        unit_id=unit_id,
                        is_required=attr_data.is_required,
                        sort_order=attr_data.sort_order,
                    )
                )
        _sync_type_units(
            db,
            product_type_id=command.product_type_id,
            payload_units=payload.product_type_units or [],
        )
        db.flush()
        attrs = db.query(models.ProductAttribute).filter(models.ProductAttribute.product_type_id == t.id).all()
        type_units = db.query(models.ProductTypeUnit).filter(models.ProductTypeUnit.product_type_id == t.id).all()
        return schemas.ProductType(
            id=t.id,
            name=t.name,
            description=t.description,
            is_composite=t.is_composite,
            strict_units_by_type=t.strict_units_by_type,
            attributes=attrs,
            product_type_units=_serialize_type_units(type_units),
        )


class DeleteProductTypeHandler:
    def handle(self, command: DeleteProductTypeCommand, uow: AbstractUnitOfWork) -> dict:
        db = uow.session
        t = db.get(models.ProductType, command.product_type_id)
        if not t:
            raise HTTPException(status_code=404, detail="Product type not found")

        db.query(models.ProductAttribute).filter(
            models.ProductAttribute.product_type_id == command.product_type_id
        ).delete()
        db.query(models.ProductTypeUnit).filter(
            models.ProductTypeUnit.product_type_id == command.product_type_id
        ).delete()
        db.delete(t)
        return {"message": "Product type deleted successfully"}
