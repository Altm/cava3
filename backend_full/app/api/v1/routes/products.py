from typing import Callable

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder

from app.api.v1.deps.auth import PermissionChecker
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.products.commands import (
    CreateRawProductCommand,
    CreateRawProductHandler,
    UpdateRawProductCommand,
    UpdateRawProductHandler,
)
from app.application.products.queries import ListRawProductsHandler, ListRawProductsQuery

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    products = dispatch_query(uow_factory, ListRawProductsHandler(), ListRawProductsQuery())
    return jsonable_encoder(products)


@router.post("")
def create_product(
    payload: dict,
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    product = dispatch_command(uow_factory, CreateRawProductHandler(), CreateRawProductCommand(payload=payload))
    return jsonable_encoder(product)


@router.put("/{product_id}")
def update_product(
    product_id: int,
    payload: dict,
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    product = dispatch_command(
        uow_factory,
        UpdateRawProductHandler(),
        UpdateRawProductCommand(product_id=product_id, payload=payload),
    )
    return jsonable_encoder(product)
