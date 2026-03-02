from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import Product
from app.schemas.legacy import RawProductCreateIn, RawProductUpdateIn


@dataclass(frozen=True)
class CreateRawProductCommand:
    payload: RawProductCreateIn


@dataclass(frozen=True)
class UpdateRawProductCommand:
    product_id: int
    payload: RawProductUpdateIn


class CreateRawProductHandler:
    def handle(self, command: CreateRawProductCommand, uow: AbstractUnitOfWork) -> Product:
        product = Product(**command.payload.model_dump(exclude_none=True))
        uow.session.add(product)
        uow.session.flush()
        return product


class UpdateRawProductHandler:
    def handle(self, command: UpdateRawProductCommand, uow: AbstractUnitOfWork) -> Product:
        product = uow.session.get(Product, command.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Not found")
        for key, value in command.payload.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        uow.session.flush()
        return product
