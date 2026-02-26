from __future__ import annotations

from dataclasses import dataclass

from app.application.common.uow import AbstractUnitOfWork
from app.models import models
from app.schemas import simple as schemas


@dataclass(frozen=True)
class CreateAttributeDefinitionCommand:
    payload: schemas.ProductAttributeCreate


class CreateAttributeDefinitionHandler:
    def handle(self, command: CreateAttributeDefinitionCommand, uow: AbstractUnitOfWork) -> schemas.ProductAttribute:
        db = uow.session
        attr_def = command.payload

        unit_id = None
        if attr_def.unit_id:
            unit = db.get(models.Unit, attr_def.unit_id)
            if unit:
                unit_id = unit.id

        db_def = models.ProductAttribute(
            product_type_id=attr_def.product_type_id,
            name=attr_def.name,
            code=attr_def.code,
            data_type=attr_def.data_type,
            unit_id=unit_id,
            is_required=attr_def.is_required,
            sort_order=attr_def.sort_order,
        )
        db.add(db_def)
        db.flush()
        return schemas.ProductAttribute.model_validate(db_def)
