import logging
from datetime import datetime
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
from app.application.simple_catalog.lots import (
    GetLotHandler,
    GetLotQuery,
    ListLotsHandler,
    ListLotsQuery,
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
    GetProductRecipeHistoryHandler,
    GetProductRecipeHistoryQuery,
    GetProductQuery,
    GetProductViewHandler,
    GetProductViewQuery,
    ListProductsHandler,
    ListProductsQuery,
    ProductsCountHandler,
    ProductsCountQuery,
    SetProductGlassLinkCommand,
    SetProductGlassLinkHandler,
    UpdateProductCommand,
    UpdateProductHandler,
    UploadProductImageCommand,
    UploadProductImageHandler,
)
from app.application.simple_catalog.prices import (
    CreatePriceRevisionCommand,
    CreatePriceRevisionHandler,
    GetCurrentPriceHandler,
    GetCurrentPriceQuery,
    GetPriceRevisionHandler,
    GetPriceRevisionQuery,
    ListPriceCalculatorsHandler,
    ListPriceCalculatorsQuery,
    ListPriceRevisionsHandler,
    ListPriceRevisionsQuery,
)
from app.application.simple_catalog.sales import (
    ConfirmSaleCommand,
    ConfirmSaleHandler,
    GetSaleHandler,
    GetSaleQuery,
    ListSalesHandler,
    ListSalesQuery,
    SaleCheckoutCommand,
    SalesCheckoutHandler,
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
    """Возвращает справочник единиц измерения."""
    return dispatch_query(uow_factory, ListUnitsHandler(), ListUnitsQuery())


@router.post("/units/", response_model=schemas.Unit)
def create_unit(
    unit: schemas.UnitCreate,
    user=Depends(PermissionChecker(["unit.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт новую единицу измерения."""
    return dispatch_command(uow_factory, CreateUnitHandler(), CreateUnitCommand(payload=unit))


@router.get("/product-types/", response_model=List[schemas.ProductType])
def get_product_types(
    user=Depends(PermissionChecker(["product_type.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список типов товаров."""
    return dispatch_query(uow_factory, ListProductTypesHandler(), ListProductTypesQuery())


@router.get("/product-types/{product_type_id}", response_model=schemas.ProductType)
def get_product_type(
    product_type_id: int,
    user=Depends(PermissionChecker(["product_type.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает тип товара по id."""
    return dispatch_query(uow_factory, GetProductTypeHandler(), GetProductTypeQuery(product_type_id=product_type_id))


@router.post("/product-types/", response_model=schemas.ProductType)
def create_product_type(
    payload: schemas.ProductTypeCreate,
    user=Depends(PermissionChecker(["product_type.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт тип товара."""
    return dispatch_command(uow_factory, CreateProductTypeHandler(), CreateProductTypeCommand(payload=payload))


@router.put("/product-types/{product_type_id}", response_model=schemas.ProductType)
def update_product_type(
    product_type_id: int,
    payload: schemas.ProductTypeUpdate,
    user=Depends(PermissionChecker(["product_type.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Обновляет тип товара."""
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
    """Удаляет тип товара."""
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
    """Создаёт определение атрибута товара."""
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
    """Создаёт товар."""
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
    """Возвращает список товаров с фильтрами и пагинацией."""
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
    """Возвращает количество товаров по фильтрам."""
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
    """Возвращает товар по id."""
    return dispatch_query(uow_factory, GetProductHandler(), GetProductQuery(product_id=product_id))


@router.get("/products/{product_id}/view", response_model=schemas.ProductView)
def get_product_view(
    product_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает детальную карточку товара для просмотра."""
    return dispatch_query(uow_factory, GetProductViewHandler(), GetProductViewQuery(product_id=product_id))


@router.get("/products/{product_id}/recipes/history", response_model=schemas.ProductRecipeHistoryOut)
def get_product_recipe_history(
    product_id: int,
    active_at: Optional[datetime] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает историю версий рецепта товара с фильтрацией по дате действия."""
    return dispatch_query(
        uow_factory,
        GetProductRecipeHistoryHandler(),
        GetProductRecipeHistoryQuery(
            product_id=product_id,
            active_at=active_at,
            date_from=date_from,
            date_to=date_to,
        ),
    )


@router.post("/products/{product_id}/image", response_model=schemas.ProductImageOut)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Загружает/обновляет изображение товара."""
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
    """Обновляет товар по id."""
    return dispatch_command(
        uow_factory,
        UpdateProductHandler(),
        UpdateProductCommand(product_id=product_id, payload=product_update),
    )


@router.put("/products/{product_id}/glass-link", response_model=schemas.ProductGlassLinkOut)
def set_product_glass_link(
    product_id: int,
    payload: schemas.ProductGlassLinkUpdate,
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Быстро настраивает связь «бутылка ↔ бокал» для товара."""
    return dispatch_command(
        uow_factory,
        SetProductGlassLinkHandler(),
        SetProductGlassLinkCommand(product_id=product_id, payload=payload),
    )


@router.put("/products/{product_id}/fraction-link", response_model=schemas.ProductGlassLinkOut)
def set_product_fraction_link(
    product_id: int,
    payload: schemas.ProductGlassLinkUpdate,
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Быстро настраивает связь «крупная единица ↔ дробная часть» для товара."""
    return dispatch_command(
        uow_factory,
        SetProductGlassLinkHandler(),
        SetProductGlassLinkCommand(product_id=product_id, payload=payload),
    )


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    user=Depends(PermissionChecker(["product.delete"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Удаляет товар по id."""
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
    """Возвращает конверсии единиц (legacy API)."""
    logger.warning("UnitConversion API is deprecated. Use ProductUnit for product-specific conversions.")
    return dispatch_query(uow_factory, ListUnitConversionsHandler(), ListUnitConversionsQuery())


@router.post("/unit-conversions/", response_model=schemas.UnitConversionSchema)
def create_unit_conversion(
    conversion: schemas.UnitConversionSchema,
    user=Depends(PermissionChecker(["unit_conversion.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт конверсию единиц (legacy API)."""
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
    """Возвращает список локаций."""
    return dispatch_query(uow_factory, ListLocationsHandler(), ListLocationsQuery())


@router.post("/locations/", response_model=schemas.Location)
def create_location(
    location: schemas.LocationBase,
    user=Depends(PermissionChecker(["location.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт новую локацию."""
    return dispatch_command(uow_factory, CreateLocationHandler(), CreateLocationCommand(payload=location))


@router.get("/prices/calculators", response_model=List[schemas.PriceCalculatorOut])
def list_price_calculators(
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список доступных файловых калькуляторов цен."""
    return dispatch_query(
        uow_factory,
        ListPriceCalculatorsHandler(),
        ListPriceCalculatorsQuery(),
    )


@router.post("/prices/revisions", response_model=schemas.PriceRevisionDetailOut)
def create_price_revision(
    payload: schemas.PriceRevisionCreate,
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт новую ревизию прайса для локации и обновляет текущие цены."""
    return dispatch_command(
        uow_factory,
        CreatePriceRevisionHandler(),
        CreatePriceRevisionCommand(payload=payload, created_by_user_id=getattr(user, "id", None)),
    )


@router.get("/prices/revisions", response_model=List[schemas.PriceRevisionListOut])
def list_price_revisions(
    location_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает историю ревизий прайсов."""
    return dispatch_query(
        uow_factory,
        ListPriceRevisionsHandler(),
        ListPriceRevisionsQuery(
            location_id=location_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/prices/revisions/{revision_id}", response_model=schemas.PriceRevisionDetailOut)
def get_price_revision(
    revision_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает содержимое выбранной ревизии прайса."""
    return dispatch_query(
        uow_factory,
        GetPriceRevisionHandler(),
        GetPriceRevisionQuery(revision_id=revision_id),
    )


@router.get("/prices/current", response_model=schemas.PriceCurrentOut)
def get_current_prices(
    location_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает последний (текущий) прайс для локации."""
    return dispatch_query(
        uow_factory,
        GetCurrentPriceHandler(),
        GetCurrentPriceQuery(location_id=location_id),
    )


@router.get("/lots", response_model=List[schemas.LotListOut])
def list_lots(
    location_id: Optional[int] = None,
    product_id: Optional[int] = None,
    lot_id: Optional[int] = None,
    include_empty: bool = False,
    limit: int = 200,
    offset: int = 0,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список партий с остатком и базовой стоимостью партии."""
    return dispatch_query(
        uow_factory,
        ListLotsHandler(),
        ListLotsQuery(
            location_id=location_id,
            product_id=product_id,
            lot_id=lot_id,
            include_empty=include_empty,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/lots/{lot_id}", response_model=schemas.LotDetailOut)
def get_lot(
    lot_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает состав партии: item, статусы, коробки и локации."""
    return dispatch_query(
        uow_factory,
        GetLotHandler(),
        GetLotQuery(lot_id=lot_id),
    )


@router.post("/sales/")
def sell_product(
    sale_request: schemas.SaleRequest,
    user=Depends(PermissionChecker(["sale.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Проводит продажу товара по legacy сценарию."""
    return dispatch_command(uow_factory, SellProductHandler(), SellProductCommand(payload=sale_request))


@router.post("/sales/checkout", response_model=schemas.SaleCheckoutOut)
def checkout_sales(
    payload: schemas.SaleCheckoutRequest,
    user=Depends(PermissionChecker(["sale.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Проводит продажу через единый checkout orchestration."""
    return dispatch_command(
        uow_factory,
        SalesCheckoutHandler(),
        SaleCheckoutCommand(payload=payload, user_id=None),
    )


@router.get("/sales/list", response_model=List[schemas.SaleListItemOut])
def get_sales_list(
    status: Optional[str] = None,
    location_id: Optional[int] = None,
    terminal_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    user=Depends(PermissionChecker(["sale.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список событий продаж с фильтрами."""
    return dispatch_query(
        uow_factory,
        ListSalesHandler(),
        ListSalesQuery(
            status=status,
            location_id=location_id,
            terminal_id=terminal_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        ),
    )


@router.get("/sales/{sale_event_id}", response_model=schemas.SaleDetailOut)
def get_sale(
    sale_event_id: int,
    user=Depends(PermissionChecker(["sale.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает детальную карточку продажи."""
    return dispatch_query(
        uow_factory,
        GetSaleHandler(),
        GetSaleQuery(sale_event_id=sale_event_id),
    )


@router.post("/sales/{sale_event_id}/confirm", response_model=schemas.SaleDetailOut)
def confirm_sale(
    sale_event_id: int,
    user=Depends(PermissionChecker(["sale.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Подтверждает продажу и переводит её в confirmed."""
    return dispatch_command(
        uow_factory,
        ConfirmSaleHandler(),
        ConfirmSaleCommand(sale_event_id=sale_event_id),
    )


@router.post("/glass-sales/")
def sell_wine_glass(
    sale_request: schemas.SaleRequest,
    user=Depends(PermissionChecker(["sale.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Проводит продажу бокала вина (legacy сценарий)."""
    return dispatch_command(uow_factory, SellWineGlassHandler(), SellWineGlassCommand(payload=sale_request))


@router.put("/units/{unit_id}", response_model=schemas.Unit)
def update_unit(
    unit_id: int,
    unit_update: schemas.UnitUpdate,
    user=Depends(PermissionChecker(["unit.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Обновляет единицу измерения."""
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
    """Удаляет единицу измерения."""
    return dispatch_command(uow_factory, DeleteUnitHandler(), DeleteUnitCommand(unit_id=unit_id))
