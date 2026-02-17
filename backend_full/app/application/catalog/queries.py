from __future__ import annotations

from dataclasses import dataclass

from app.application.common.uow import AbstractUnitOfWork
from app.services.catalog_service import CatalogService


@dataclass(frozen=True)
class GetCatalogQuery:
    location: int


class GetCatalogHandler:
    def handle(self, query: GetCatalogQuery, uow: AbstractUnitOfWork) -> dict:
        service = CatalogService(uow.session)
        return {"location_id": query.location, "items": service.catalog_for_location(query.location)}
