from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import Product


@dataclass(frozen=True)
class CreateRawProductCommand:
    payload: dict


@dataclass(frozen=True)
class UpdateRawProductCommand:
    product_id: int
    payload: dict


class CreateRawProductHandler:
    def handle(self, command: CreateRawProductCommand, uow: AbstractUnitOfWork) -> Product:
        product = Product(**command.payload)
        uow.session.add(product)
        uow.session.flush()
        return product


class UpdateRawProductHandler:
    def handle(self, command: UpdateRawProductCommand, uow: AbstractUnitOfWork) -> Product:
        product = uow.session.query(Product).get(command.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Not found")
        for key, value in command.payload.items():
            setattr(product, key, value)
        uow.session.flush()
        return product
