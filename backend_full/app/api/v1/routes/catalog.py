from typing import Callable

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps.auth import PermissionChecker
from app.api.v1.deps.uow import get_uow_factory
from app.application.catalog.queries import GetCatalogHandler, GetCatalogQuery
from app.application.common import dispatch_query
from app.application.common.uow import AbstractUnitOfWork

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("")
def get_catalog(
    location: int = Query(...),
    user=Depends(PermissionChecker(["catalog.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает каталог товаров для указанной локации."""
    return dispatch_query(uow_factory, GetCatalogHandler(), GetCatalogQuery(location=location))
