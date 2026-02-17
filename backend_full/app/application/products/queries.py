from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.application.common.uow import AbstractUnitOfWork
from app.models.models import Product


@dataclass(frozen=True)
class ListRawProductsQuery:
    pass


class ListRawProductsHandler:
    def handle(self, query: ListRawProductsQuery, uow: AbstractUnitOfWork) -> List[Product]:
        return uow.session.query(Product).all()
