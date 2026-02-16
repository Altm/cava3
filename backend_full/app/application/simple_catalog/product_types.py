from __future__ import annotations

from dataclasses import dataclass
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


class ListProductTypesHandler:
    def handle(self, query: ListProductTypesQuery, uow: AbstractUnitOfWork) -> List[schemas.ProductType]:
        db = uow.session
        types = db.query(models.ProductType).all()
        result: list[schemas.ProductType] = []
        for t in types:
            attrs = db.query(models.ProductAttribute).filter(models.ProductAttribute.product_type_id == t.id).all()
            result.append(
                schemas.ProductType(
                    id=t.id,
                    name=t.name,
                    description=t.description,
                    is_composite=t.is_composite,
                    attributes=attrs,
                )
            )
        return result


class GetProductTypeHandler:
    def handle(self, query: GetProductTypeQuery, uow: AbstractUnitOfWork) -> schemas.ProductType:
        db = uow.session
        t = db.query(models.ProductType).get(query.product_type_id)
        if not t:
            raise HTTPException(status_code=404, detail="Product type not found")
        attrs = db.query(models.ProductAttribute).filter(models.ProductAttribute.product_type_id == t.id).all()
        return schemas.ProductType(
            id=t.id,
            name=t.name,
            description=t.description,
            is_composite=t.is_composite,
            attributes=attrs,
        )


class CreateProductTypeHandler:
    def handle(self, command: CreateProductTypeCommand, uow: AbstractUnitOfWork) -> schemas.ProductType:
        db = uow.session
        payload = command.payload
        t = models.ProductType(name=payload.name, description=payload.description, is_composite=payload.is_composite)
        db.add(t)
        db.flush()

        if payload.attributes:
            for attr_data in payload.attributes:
                unit_id = None
                if attr_data.unit_id:
                    unit = db.query(models.Unit).get(attr_data.unit_id)
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
        db.flush()
        attrs = db.query(models.ProductAttribute).filter(models.ProductAttribute.product_type_id == t.id).all()
        return schemas.ProductType(
            id=t.id,
            name=t.name,
            description=t.description,
            is_composite=t.is_composite,
            attributes=attrs,
        )


class UpdateProductTypeHandler:
    def handle(self, command: UpdateProductTypeCommand, uow: AbstractUnitOfWork) -> schemas.ProductType:
        db = uow.session
        t = db.query(models.ProductType).get(command.product_type_id)
        if not t:
            raise HTTPException(status_code=404, detail="Product type not found")

        payload = command.payload
        t.name = payload.name
        t.description = payload.description
        t.is_composite = payload.is_composite

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
                    unit = db.query(models.Unit).get(attr_data.unit_id)
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
        db.flush()
        attrs = db.query(models.ProductAttribute).filter(models.ProductAttribute.product_type_id == t.id).all()
        return schemas.ProductType(
            id=t.id,
            name=t.name,
            description=t.description,
            is_composite=t.is_composite,
            attributes=attrs,
        )


class DeleteProductTypeHandler:
    def handle(self, command: DeleteProductTypeCommand, uow: AbstractUnitOfWork) -> dict:
        db = uow.session
        t = db.query(models.ProductType).get(command.product_type_id)
        if not t:
            raise HTTPException(status_code=404, detail="Product type not found")

        db.query(models.ProductAttribute).filter(
            models.ProductAttribute.product_type_id == command.product_type_id
        ).delete()
        db.delete(t)
        return {"message": "Product type deleted successfully"}
