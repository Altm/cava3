from __future__ import annotations

from dataclasses import dataclass
from typing import List

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.schemas import simple as schemas


@dataclass(frozen=True)
class ListUnitConversionsQuery:
    pass


@dataclass(frozen=True)
class CreateUnitConversionCommand:
    payload: schemas.UnitConversionSchema


class ListUnitConversionsHandler:
    def handle(self, query: ListUnitConversionsQuery, uow: AbstractUnitOfWork) -> List[schemas.UnitConversionSchema]:
        return []


class CreateUnitConversionHandler:
    def handle(self, command: CreateUnitConversionCommand, uow: AbstractUnitOfWork) -> schemas.UnitConversionSchema:
        raise HTTPException(
            status_code=400,
            detail="UnitConversion API is deprecated. Use ProductUnit for product-specific conversions.",
        )
