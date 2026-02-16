from __future__ import annotations

from dataclasses import dataclass
from typing import List

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models import models
from app.models.models import Adjustment, PriceList, ProductAttribute, ProductComposite, ProductUnit, SaleLine, Stock, Transfer
from app.schemas import simple as schemas


@dataclass(frozen=True)
class ListUnitsQuery:
    pass


@dataclass(frozen=True)
class CreateUnitCommand:
    payload: schemas.UnitCreate


@dataclass(frozen=True)
class UpdateUnitCommand:
    unit_id: int
    payload: schemas.UnitUpdate


@dataclass(frozen=True)
class DeleteUnitCommand:
    unit_id: int


class ListUnitsHandler:
    def handle(self, query: ListUnitsQuery, uow: AbstractUnitOfWork) -> List[schemas.Unit]:
        db = uow.session
        units = db.query(models.Unit).all()
        return [
            schemas.Unit(
                id=u.id,
                code=u.code,
                description=u.description,
                unit_type=u.unit_type,
                is_discrete=u.is_discrete,
            )
            for u in units
        ]


class CreateUnitHandler:
    def handle(self, command: CreateUnitCommand, uow: AbstractUnitOfWork) -> schemas.Unit:
        db = uow.session
        unit = command.payload
        existing_unit = db.query(models.Unit).filter(models.Unit.code == unit.code).first()
        if existing_unit:
            raise HTTPException(status_code=400, detail="Unit with this code already exists")

        db_unit = models.Unit(
            code=unit.code,
            description=unit.description,
            unit_type=unit.unit_type or "base",
            is_discrete=unit.is_discrete if unit.is_discrete is not None else True,
        )
        db.add(db_unit)
        db.flush()
        return schemas.Unit(
            id=db_unit.id,
            code=db_unit.code,
            description=db_unit.description,
            unit_type=db_unit.unit_type,
            is_discrete=db_unit.is_discrete,
        )


class UpdateUnitHandler:
    def handle(self, command: UpdateUnitCommand, uow: AbstractUnitOfWork) -> schemas.Unit:
        db = uow.session
        db_unit = db.query(models.Unit).get(command.unit_id)
        if not db_unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        unit_update = command.payload
        existing_unit = db.query(models.Unit).filter(
            models.Unit.code == unit_update.code,
            models.Unit.id != command.unit_id,
        ).first()
        if existing_unit:
            raise HTTPException(status_code=400, detail="Unit with this code already exists")

        db_unit.code = unit_update.code
        db_unit.description = unit_update.description
        db_unit.unit_type = unit_update.unit_type
        db_unit.is_discrete = unit_update.is_discrete
        db.flush()
        return schemas.Unit(
            id=db_unit.id,
            code=db_unit.code,
            description=db_unit.description,
            unit_type=db_unit.unit_type,
            is_discrete=db_unit.is_discrete,
        )


class DeleteUnitHandler:
    def handle(self, command: DeleteUnitCommand, uow: AbstractUnitOfWork) -> dict:
        db = uow.session
        unit_id = command.unit_id
        db_unit = db.query(models.Unit).get(unit_id)
        if not db_unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        product_unit_count = db.query(ProductUnit).filter(ProductUnit.unit_id == unit_id).count()
        if product_unit_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by product units")

        stock_count = db.query(Stock).filter(Stock.unit_id == unit_id).count()
        if stock_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by stock records")

        price_list_count = db.query(PriceList).filter(PriceList.unit_id == unit_id).count()
        if price_list_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by price lists")

        adjustment_count = db.query(Adjustment).filter(Adjustment.unit_id == unit_id).count()
        if adjustment_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by adjustments")

        transfer_count = db.query(Transfer).filter(Transfer.unit_id == unit_id).count()
        if transfer_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by transfers")

        sale_line_count = db.query(SaleLine).filter(SaleLine.unit_id == unit_id).count()
        if sale_line_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by sale lines")

        attr_def_count = db.query(ProductAttribute).filter(ProductAttribute.unit_id == unit_id).count()
        if attr_def_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by attribute definitions")

        comp_count = db.query(ProductComposite).filter(ProductComposite.unit_id == unit_id).count()
        if comp_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by composite components")

        db.delete(db_unit)
        return {"message": "Unit deleted successfully"}
