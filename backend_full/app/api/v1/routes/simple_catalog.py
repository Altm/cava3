import logging
from typing import Callable, List, Optional

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.v1.deps.auth import PermissionChecker
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.simple_catalog.attributes import (
    CreateAttributeDefinitionCommand,
    CreateAttributeDefinitionHandler,
)
from app.application.simple_catalog.locations import (
    CreateLocationCommand,
    CreateLocationHandler,
    ListLocationsHandler,
    ListLocationsQuery,
)
from app.application.simple_catalog.product_types import (
    CreateProductTypeCommand,
    CreateProductTypeHandler,
    DeleteProductTypeCommand,
    DeleteProductTypeHandler,
    GetProductTypeHandler,
    GetProductTypeQuery,
    ListProductTypesHandler,
    ListProductTypesQuery,
    UpdateProductTypeCommand,
    UpdateProductTypeHandler,
)
from app.application.simple_catalog.products import (
    CreateProductCommand,
    CreateProductHandler,
    DeleteProductCommand,
    DeleteProductHandler,
    GetProductHandler,
    GetProductQuery,
    GetProductViewHandler,
    GetProductViewQuery,
    ListProductsHandler,
    ListProductsQuery,
    ProductsCountHandler,
    ProductsCountQuery,
    UpdateProductCommand,
    UpdateProductHandler,
    UploadProductImageCommand,
    UploadProductImageHandler,
)
from app.application.simple_catalog.sales import (
    SellProductCommand,
    SellProductHandler,
    SellWineGlassCommand,
    SellWineGlassHandler,
)
from app.application.simple_catalog.unit_conversions import (
    CreateUnitConversionCommand,
    CreateUnitConversionHandler,
    ListUnitConversionsHandler,
    ListUnitConversionsQuery,
)
from app.application.simple_catalog.units import (
    CreateUnitCommand,
    CreateUnitHandler,
    DeleteUnitCommand,
    DeleteUnitHandler,
    ListUnitsHandler,
    ListUnitsQuery,
    UpdateUnitCommand,
    UpdateUnitHandler,
)
from app.schemas import simple as schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simple-catalog", tags=["simple-catalog"])


@router.get("/units/", response_model=List[schemas.Unit])
def get_units(
    user=Depends(PermissionChecker(["unit.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, ListUnitsHandler(), ListUnitsQuery())


@router.post("/units/", response_model=schemas.Unit)
def create_unit(
    unit: schemas.UnitCreate,
    user=Depends(PermissionChecker(["unit.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(uow_factory, CreateUnitHandler(), CreateUnitCommand(payload=unit))


@router.get("/product-types/", response_model=List[schemas.ProductType])
def get_product_types(
    user=Depends(PermissionChecker(["product_type.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, ListProductTypesHandler(), ListProductTypesQuery())


@router.get("/product-types/{product_type_id}", response_model=schemas.ProductType)
def get_product_type(
    product_type_id: int,
    user=Depends(PermissionChecker(["product_type.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, GetProductTypeHandler(), GetProductTypeQuery(product_type_id=product_type_id))


@router.post("/product-types/", response_model=schemas.ProductType)
def create_product_type(
    payload: schemas.ProductTypeCreate,
    user=Depends(PermissionChecker(["product_type.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(uow_factory, CreateProductTypeHandler(), CreateProductTypeCommand(payload=payload))


@router.put("/product-types/{product_type_id}", response_model=schemas.ProductType)
def update_product_type(
    product_type_id: int,
    payload: schemas.ProductTypeUpdate,
    user=Depends(PermissionChecker(["product_type.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        UpdateProductTypeHandler(),
        UpdateProductTypeCommand(product_type_id=product_type_id, payload=payload),
    )


@router.delete("/product-types/{product_type_id}")
def delete_product_type(
    product_type_id: int,
    user=Depends(PermissionChecker(["product_type.delete"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        DeleteProductTypeHandler(),
        DeleteProductTypeCommand(product_type_id=product_type_id),
    )


@router.post("/attribute-definitions/", response_model=schemas.ProductAttribute)
def create_attribute_definition(
    attr_def: schemas.ProductAttributeCreate,
    user=Depends(PermissionChecker(["attribute_definition.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        CreateAttributeDefinitionHandler(),
        CreateAttributeDefinitionCommand(payload=attr_def),
    )


@router.post("/products/", response_model=schemas.Product)
def create_product(
    product: schemas.ProductCreate,
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(uow_factory, CreateProductHandler(), CreateProductCommand(payload=product))


@router.get("/products/", response_model=List[schemas.Product])
def get_products(
    location_id: Optional[int] = None,
    product_type_id: Optional[int] = None,
    name: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(
        uow_factory,
        ListProductsHandler(),
        ListProductsQuery(
            location_id=location_id,
            product_type_id=product_type_id,
            name=name,
            skip=skip,
            limit=limit,
        ),
    )


@router.get("/products-count/")
def get_products_count(
    location_id: Optional[int] = None,
    product_type_id: Optional[int] = None,
    name: Optional[str] = None,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(
        uow_factory,
        ProductsCountHandler(),
        ProductsCountQuery(location_id=location_id, product_type_id=product_type_id, name=name),
    )


@router.get("/products/{product_id}", response_model=schemas.Product)
def get_product(
    product_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, GetProductHandler(), GetProductQuery(product_id=product_id))


@router.get("/products/{product_id}/view", response_model=schemas.ProductView)
def get_product_view(
    product_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, GetProductViewHandler(), GetProductViewQuery(product_id=product_id))


@router.post("/products/{product_id}/image", response_model=schemas.ProductImageOut)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    content = await file.read()
    return dispatch_command(
        uow_factory,
        UploadProductImageHandler(),
        UploadProductImageCommand(
            product_id=product_id,
            filename=file.filename or "image.jpg",
            content_type=file.content_type or "",
            content=content,
        ),
    )


@router.put("/products/{product_id}", response_model=schemas.Product)
def update_product(
    product_id: int,
    product_update: schemas.ProductUpdate,
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        UpdateProductHandler(),
        UpdateProductCommand(product_id=product_id, payload=product_update),
    )


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    user=Depends(PermissionChecker(["product.delete"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        DeleteProductHandler(),
        DeleteProductCommand(product_id=product_id),
    )


@router.get("/unit-conversions/", response_model=List[schemas.UnitConversionSchema])
def get_unit_conversions(
    user=Depends(PermissionChecker(["unit_conversion.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    logger.warning("UnitConversion API is deprecated. Use ProductUnit for product-specific conversions.")
    return dispatch_query(uow_factory, ListUnitConversionsHandler(), ListUnitConversionsQuery())


@router.post("/unit-conversions/", response_model=schemas.UnitConversionSchema)
def create_unit_conversion(
    conversion: schemas.UnitConversionSchema,
    user=Depends(PermissionChecker(["unit_conversion.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    logger.error("UnitConversion API is deprecated. Use ProductUnit for product-specific conversions.")
    return dispatch_command(
        uow_factory,
        CreateUnitConversionHandler(),
        CreateUnitConversionCommand(payload=conversion),
    )


@router.get("/locations/", response_model=List[schemas.Location])
def get_locations(
    user=Depends(PermissionChecker(["location.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, ListLocationsHandler(), ListLocationsQuery())


@router.post("/locations/", response_model=schemas.Location)
def create_location(
    location: schemas.LocationBase,
    user=Depends(PermissionChecker(["location.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(uow_factory, CreateLocationHandler(), CreateLocationCommand(payload=location))


@router.post("/sales/")
def sell_product(
    sale_request: schemas.SaleRequest,
    user=Depends(PermissionChecker(["sale.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(uow_factory, SellProductHandler(), SellProductCommand(payload=sale_request))


@router.post("/glass-sales/")
def sell_wine_glass(
    sale_request: schemas.SaleRequest,
    user=Depends(PermissionChecker(["sale.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(uow_factory, SellWineGlassHandler(), SellWineGlassCommand(payload=sale_request))


@router.put("/units/{unit_id}", response_model=schemas.Unit)
def update_unit(
    unit_id: int,
    unit_update: schemas.UnitUpdate,
    user=Depends(PermissionChecker(["unit.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(
        uow_factory,
        UpdateUnitHandler(),
        UpdateUnitCommand(unit_id=unit_id, payload=unit_update),
    )


@router.delete("/units/{unit_id}")
def delete_unit(
    unit_id: int,
    user=Depends(PermissionChecker(["unit.delete"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_command(uow_factory, DeleteUnitHandler(), DeleteUnitCommand(unit_id=unit_id))
