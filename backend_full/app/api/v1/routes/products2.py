"""
Products 2 API - Enhanced product management with fractional units support.
"""
from typing import Callable, Optional
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from fastapi.encoders import jsonable_encoder

from app.api.v1.deps.auth import PermissionChecker
from app.api.v1.deps.uow import get_uow_factory
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.simple_catalog.products import (
    CreateProductCommand,
    ListProductsQuery,
    ProductsCountQuery,
    GetProductQuery,
    GetProductViewQuery,
    UpdateProductCommand,
    DeleteProductCommand,
    CreateProductHandler,
    ListProductsHandler,
    ProductsCountHandler,
    GetProductHandler,
    GetProductViewHandler,
    UpdateProductHandler,
    DeleteProductHandler,
    UploadProductImageCommand,
    UploadProductImageHandler,
)
from app.models import models
from app.schemas import simple as schemas
from sqlalchemy.orm import Session
from app.infrastructure.db.session import SessionLocal
from app.application.simple_catalog.common import ProductAvailabilityCalculator, default_location, serialize_product_view

router = APIRouter(prefix="/products2", tags=["products2"])


def get_db_session() -> Session:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _active_recipe(db: Session, product_id: int) -> models.ProductRecipe | None:
    now = datetime.utcnow()
    return (
        db.query(models.ProductRecipe)
        .filter(
            models.ProductRecipe.product_id == product_id,
            models.ProductRecipe.is_active.is_(True),
            models.ProductRecipe.valid_from <= now,
            (models.ProductRecipe.valid_to.is_(None) | (models.ProductRecipe.valid_to > now)),
        )
        .order_by(models.ProductRecipe.version.desc(), models.ProductRecipe.id.desc())
        .first()
    )


@router.get("")
def list_products(
    location_id: Optional[int] = Query(None),
    product_type_id: Optional[int] = Query(None),
    name: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает список продуктов с расширенной информацией о дробных единицах."""
    from sqlalchemy.orm import joinedload
    from app.models import models as models_module
    
    products = dispatch_query(
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
    return jsonable_encoder(products)


@router.get("/count")
def get_products_count(
    location_id: Optional[int] = Query(None),
    product_type_id: Optional[int] = Query(None),
    name: Optional[str] = Query(None),
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает общее количество продуктов по фильтрам."""
    result = dispatch_query(
        uow_factory,
        ProductsCountHandler(),
        ProductsCountQuery(
            location_id=location_id,
            product_type_id=product_type_id,
            name=name,
        ),
    )
    return result


@router.get("/{product_id}")
def get_product(
    product_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает продукт с компонентами и единицами измерения."""
    product = dispatch_query(
        uow_factory,
        GetProductHandler(),
        GetProductQuery(product_id=product_id),
    )
    return jsonable_encoder(product)


@router.get("/{product_id}/view")
def get_product_view(
    product_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает расширенную информацию о продукте с деревом компонентов и остатками."""
    product_view = dispatch_query(
        uow_factory,
        GetProductViewHandler(),
        GetProductQuery(product_id=product_id),
    )
    return jsonable_encoder(product_view)


@router.post("")
def create_product(
    payload: schemas.ProductCreate,
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Создаёт продукт с поддержкой дробных единиц и компонентов."""
    product = dispatch_command(
        uow_factory,
        CreateProductHandler(),
        CreateProductCommand(payload=payload),
    )
    return jsonable_encoder(product)


@router.put("/{product_id}")
def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Обновляет продукт с поддержкой дробных единиц и компонентов."""
    product = dispatch_command(
        uow_factory,
        UpdateProductHandler(),
        UpdateProductCommand(product_id=product_id, payload=payload),
    )
    return jsonable_encoder(product)


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    user=Depends(PermissionChecker(["product.delete"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Удаляет продукт."""
    dispatch_command(
        uow_factory,
        DeleteProductHandler(),
        DeleteProductCommand(product_id=product_id),
    )
    return {"message": "Product deleted"}


@router.post("/{product_id}/image")
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    user=Depends(PermissionChecker(["product.write"])),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
    db: Session = Depends(get_db_session),
):
    """Загружает изображение продукта."""
    content = file.file.read()
    command = UploadProductImageCommand(
        product_id=product_id,
        filename=file.filename or "image.jpg",
        content_type=file.content_type or "image/jpeg",
        content=content,
    )
    result = dispatch_command(uow_factory, UploadProductImageHandler(), command)
    return jsonable_encoder(result)


@router.get("/{product_id}/component-tree")
def get_component_tree(
    product_id: int,
    location_id: Optional[int] = Query(None),
    user=Depends(PermissionChecker(["product.read"])),
    db: Session = Depends(get_db_session),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """
    Возвращает дерево компонентов продукта с доступностью.
    
    Для составных продуктов показывает рекурсивную структуру всех компонентов
    с текущими остатками и доступностью для продажи.
    """
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    location = default_location(db)
    if location_id:
        location = db.get(models.Location, location_id) or location
    
    calculator = ProductAvailabilityCalculator(db, location.id)
    product_view = serialize_product_view(product, db, calculator=calculator)
    return jsonable_encoder(product_view.component_tree)


@router.get("/{product_id}/fractional-units")
def get_fractional_units(
    product_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    db: Session = Depends(get_db_session),
):
    """
    Возвращает все дробные единицы продукта с коэффициентами.
    
    Пример для вина:
    - bottle (базовая) = 1.0
    - glass = 0.1667 (1/6 бутылки)
    
    Пример для хлеба:
    - kg (базовая) = 1.0
    - slice = 0.05 (50г от 1кг)
    """
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    units = (
        db.query(models.ProductUnit)
        .join(models.Unit)
        .filter(models.ProductUnit.product_id == product_id)
        .all()
    )
    
    result = []
    for pu in units:
        result.append({
            "id": pu.id,
            "unit_id": pu.unit_id,
            "unit_code": pu.unit.code,
            "unit_description": pu.unit.description,
            "unit_type": pu.unit.unit_type,
            "ratio_to_base": str(pu.ratio_to_base),
            "discrete_step": str(pu.discrete_step) if pu.discrete_step else None,
            "is_base": pu.unit_id == product.base_unit_id,
        })
    
    return result


@router.post("/{product_id}/fractional-units")
def add_fractional_unit(
    product_id: int,
    payload: schemas.ProductUnitCreate,
    user=Depends(PermissionChecker(["product.write"])),
    db: Session = Depends(get_db_session),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """
    Добавляет дробную единицу к продукту.
    
    Пример: добавить "бокал" к вину с ratio_to_base = 0.1667
    """
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    unit = db.get(models.Unit, payload.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    # Проверка на дубликат
    existing = (
        db.query(models.ProductUnit)
        .filter(
            models.ProductUnit.product_id == product_id,
            models.ProductUnit.unit_id == payload.unit_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Unit already bound to product")
    
    # Базовая единица всегда имеет ratio = 1
    ratio = Decimal("1") if payload.unit_id == product.base_unit_id else Decimal(str(payload.ratio_to_base))
    
    product_unit = models.ProductUnit(
        product_id=product_id,
        unit_id=payload.unit_id,
        ratio_to_base=ratio,
        discrete_step=payload.discrete_step,
    )
    db.add(product_unit)
    db.commit()
    
    return jsonable_encoder({
        "id": product_unit.id,
        "unit_id": product_unit.unit_id,
        "ratio_to_base": str(product_unit.ratio_to_base),
        "discrete_step": str(product_unit.discrete_step) if product_unit.discrete_step else None,
    })


@router.put("/{product_id}/fractional-units/{unit_id}")
def update_fractional_unit(
    product_id: int,
    unit_id: int,
    payload: schemas.ProductUnitUpdate,
    user=Depends(PermissionChecker(["product.write"])),
    db: Session = Depends(get_db_session),
):
    """
    Обновляет коэффициент дробной единицы.
    
    Пример: изменить количество бокалов в бутылке
    """
    product_unit = (
        db.query(models.ProductUnit)
        .filter(
            models.ProductUnit.product_id == product_id,
            models.ProductUnit.unit_id == unit_id,
        )
        .first()
    )
    if not product_unit:
        raise HTTPException(status_code=404, detail="Product unit not found")
    
    # Нельзя изменить ratio базовой единицы
    product = db.get(models.Product, product_id)
    if product and product.base_unit_id == unit_id:
        raise HTTPException(status_code=400, detail="Cannot change base unit ratio")
    
    product_unit.ratio_to_base = Decimal(str(payload.ratio_to_base))
    if payload.discrete_step is not None:
        product_unit.discrete_step = Decimal(str(payload.discrete_step))
    
    db.commit()
    
    return jsonable_encoder({
        "id": product_unit.id,
        "ratio_to_base": str(product_unit.ratio_to_base),
        "discrete_step": str(product_unit.discrete_step) if product_unit.discrete_step else None,
    })


@router.delete("/{product_id}/fractional-units/{unit_id}")
def remove_fractional_unit(
    product_id: int,
    unit_id: int,
    user=Depends(PermissionChecker(["product.write"])),
    db: Session = Depends(get_db_session),
):
    """
    Удаляет дробную единицу из продукта.
    
    Нельзя удалить базовую единицу.
    """
    product = db.get(models.Product, product_id)
    if product and product.base_unit_id == unit_id:
        raise HTTPException(status_code=400, detail="Cannot remove base unit")
    
    product_unit = (
        db.query(models.ProductUnit)
        .filter(
            models.ProductUnit.product_id == product_id,
            models.ProductUnit.unit_id == unit_id,
        )
        .first()
    )
    if not product_unit:
        raise HTTPException(status_code=404, detail="Product unit not found")
    
    db.delete(product_unit)
    db.commit()
    
    return {"message": "Product unit removed"}


@router.get("/{product_id}/components")
def get_components(
    product_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    db: Session = Depends(get_db_session),
):
    """
    Возвращает компоненты составного продукта.
    
    Пример для бутерброда:
    - хлеб: 0.1 кг
    - томатная паста: 0.02 кг
    """
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    components = (
        db.query(models.ProductRecipeComponent)
        .join(models.ProductRecipe, models.ProductRecipe.id == models.ProductRecipeComponent.recipe_id)
        .filter(
            models.ProductRecipe.product_id == product_id,
            models.ProductRecipe.is_active.is_(True),
        )
        .order_by(models.ProductRecipeComponent.id.asc())
        .all()
    )
    
    result = []
    for comp in components:
        ingredient = db.get(models.Ingredient, comp.ingredient_id)
        primary_binding = (
            db.query(models.IngredientProductBinding)
            .filter(
                models.IngredientProductBinding.ingredient_id == comp.ingredient_id,
                models.IngredientProductBinding.is_active.is_(True),
            )
            .order_by(models.IngredientProductBinding.priority.asc(), models.IngredientProductBinding.id.asc())
            .first()
        )
        bound_product = db.get(models.Product, primary_binding.product_id) if primary_binding else None
        result.append({
            "id": comp.id,
            "ingredient_id": comp.ingredient_id,
            "ingredient_name": ingredient.name if ingredient else "Unknown",
            "ingredient_code": ingredient.code if ingredient else None,
            "bound_product_id": bound_product.id if bound_product else None,
            "bound_product_name": bound_product.name if bound_product else None,
            "quantity": str(comp.quantity),
            "unit_id": comp.unit_id,
            "unit_code": comp.unit.code if comp.unit else None,
            "substitution_allowed": comp.substitution_allowed,
            "rounding": comp.rounding,
        })
    
    return result


@router.post("/{product_id}/components")
def add_component(
    product_id: int,
    payload: schemas.ProductComponentCreate,
    user=Depends(PermissionChecker(["product.write"])),
    db: Session = Depends(get_db_session),
):
    """
    Добавляет компонент к составному продукту.
    
    Пример: добавить "хлеб 0.1 кг" к бутерброду
    """
    from app.application.simple_catalog.products import _assert_no_component_cycles
    
    parent = db.get(models.Product, product_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent product not found")
    
    ingredient = db.get(models.Ingredient, payload.ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Определение единицы измерения компонента
    unit_id = int(payload.unit_id or ingredient.base_unit_id)
    if unit_id != ingredient.base_unit_id:
        raise HTTPException(status_code=400, detail="Ingredient can be used only in its base unit")
    
    # Проверка на циклы
    active_recipe = _active_recipe(db, product_id)
    existing_ingredient_ids: list[int] = []
    if active_recipe:
        existing_ingredient_ids = [
            int(row.ingredient_id)
            for row in db.query(models.ProductRecipeComponent.ingredient_id)
            .filter(models.ProductRecipeComponent.recipe_id == active_recipe.id)
            .all()
        ]
    _assert_no_component_cycles(db, product_id, existing_ingredient_ids + [payload.ingredient_id])
    
    # Проверка на дубликат
    if not active_recipe:
        max_version = (
            db.query(models.func.max(models.ProductRecipe.version))
            .filter(models.ProductRecipe.product_id == product_id)
            .scalar()
        )
        active_recipe = models.ProductRecipe(
            product_id=product_id,
            version=int(max_version or 0) + 1,
            is_active=True,
            valid_from=datetime.utcnow(),
            valid_to=None,
        )
        db.add(active_recipe)
        db.flush()

    existing = (
        db.query(models.ProductRecipeComponent)
        .filter(
            models.ProductRecipeComponent.recipe_id == active_recipe.id,
            models.ProductRecipeComponent.ingredient_id == payload.ingredient_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Component already exists")
    
    recipe_component = models.ProductRecipeComponent(
        recipe_id=active_recipe.id,
        ingredient_id=payload.ingredient_id,
        quantity=Decimal(str(payload.quantity)),
        unit_id=unit_id,
        substitution_allowed=payload.substitution_allowed or False,
        rounding=payload.rounding,
    )
    db.add(recipe_component)
    db.commit()
    
    return jsonable_encoder({
        "id": recipe_component.id,
        "ingredient_id": recipe_component.ingredient_id,
        "quantity": str(recipe_component.quantity),
        "unit_id": recipe_component.unit_id,
    })


@router.put("/{product_id}/components/{component_id}")
def update_component(
    product_id: int,
    component_id: int,
    payload: schemas.ProductComponentUpdate,
    user=Depends(PermissionChecker(["product.write"])),
    db: Session = Depends(get_db_session),
):
    """
    Обновляет компонент составного продукта.
    
    Пример: изменить количество хлеба в бутерброде с 0.1 кг на 0.15 кг
    """
    from app.application.simple_catalog.products import _assert_no_component_cycles
    
    component = (
        db.query(models.ProductRecipeComponent)
        .join(models.ProductRecipe, models.ProductRecipe.id == models.ProductRecipeComponent.recipe_id)
        .filter(
            models.ProductRecipe.product_id == product_id,
            models.ProductRecipe.is_active.is_(True),
            models.ProductRecipeComponent.id == component_id,
        )
        .first()
    )
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    # Обновление полей
    if payload.quantity is not None:
        component.quantity = Decimal(str(payload.quantity))
    if payload.unit_id is not None:
        ingredient = db.get(models.Ingredient, component.ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")
        if int(payload.unit_id) != int(ingredient.base_unit_id):
            raise HTTPException(status_code=400, detail="Ingredient can be used only in its base unit")
        component.unit_id = payload.unit_id
    if payload.substitution_allowed is not None:
        component.substitution_allowed = payload.substitution_allowed
    if payload.rounding is not None:
        component.rounding = payload.rounding
    
    db.commit()
    
    return jsonable_encoder({
        "id": component.id,
        "quantity": str(component.quantity),
        "unit_id": component.unit_id,
    })


@router.delete("/{product_id}/components/{component_id}")
def remove_component(
    product_id: int,
    component_id: int,
    user=Depends(PermissionChecker(["product.write"])),
    db: Session = Depends(get_db_session),
):
    """Удаляет компонент из составного продукта."""
    component = (
        db.query(models.ProductRecipeComponent)
        .join(models.ProductRecipe, models.ProductRecipe.id == models.ProductRecipeComponent.recipe_id)
        .filter(
            models.ProductRecipe.product_id == product_id,
            models.ProductRecipe.is_active.is_(True),
            models.ProductRecipeComponent.id == component_id,
        )
        .first()
    )
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    db.delete(component)
    db.commit()
    
    return {"message": "Component removed"}


@router.get("/{product_id}/usage-examples")
def get_usage_examples(
    product_id: int,
    user=Depends(PermissionChecker(["product.read"])),
    db: Session = Depends(get_db_session),
):
    """
    Возвращает примеры использования продукта.
    
    Для вина показывает:
    - Продажа бутылками (целая единица)
    - Продажа бокалами (дробная единица)
    
    Для хлеба показывает:
    - Продажа кг (целая единица)
    - Продажа ломтиками (дробная единица)
    - Использование в бутербродах (как компонент)
    """
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    examples = []
    
    # 1. Продажа в базовых единицах
    examples.append({
        "type": "base_unit_sale",
        "title": f"Продажа в базовых единицах ({product.base_unit_id})",
        "description": f"Продажа целых единиц товара",
        "unit_id": product.base_unit_id,
        "ratio": "1.0",
    })
    
    # 2. Продажа в дробных единицах
    product_units = (
        db.query(models.ProductUnit)
        .join(models.Unit)
        .filter(
            models.ProductUnit.product_id == product_id,
            models.ProductUnit.unit_id != product.base_unit_id,
        )
        .all()
    )
    for pu in product_units:
        examples.append({
            "type": "fractional_unit_sale",
            "title": f"Продажа в {pu.unit.code}",
            "description": f"Продажа дробных единиц (1 {pu.unit.code} = {pu.ratio_to_base} базовой)",
            "unit_id": pu.unit_id,
            "ratio": str(pu.ratio_to_base),
        })
    
    # 3. Использование как компонента
    parent_products = (
        db.query(models.ProductRecipeComponent, models.Product, models.IngredientProductBinding)
        .join(models.ProductRecipe, models.ProductRecipe.id == models.ProductRecipeComponent.recipe_id)
        .join(models.Product, models.Product.id == models.ProductRecipe.product_id)
        .join(
            models.IngredientProductBinding,
            models.IngredientProductBinding.ingredient_id == models.ProductRecipeComponent.ingredient_id,
        )
        .filter(
            models.IngredientProductBinding.product_id == product_id,
            models.IngredientProductBinding.is_active.is_(True),
            models.ProductRecipe.is_active.is_(True),
        )
        .all()
    )
    for comp, parent, binding in parent_products:
        examples.append({
            "type": "component_usage",
            "title": f"Компонент в '{parent.name}'",
            "description": f"Используется как часть составного продукта: {comp.quantity} {comp.unit.code}",
            "parent_product_id": parent.id,
            "parent_product_name": parent.name,
            "quantity": str(comp.quantity),
            "unit_code": comp.unit.code if comp.unit else None,
            "ingredient_id": comp.ingredient_id,
            "ingredient_ratio": str(binding.ratio_to_ingredient_base),
        })
    
    return jsonable_encoder(examples)
