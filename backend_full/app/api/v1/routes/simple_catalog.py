import logging
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.api.v1.deps.auth import get_db, get_current_user, PermissionChecker, allow_public
from app.models import models
from app.schemas import simple as schemas

from app.models.models import AttributeDefinition, ProductAttributeValue, Location, ProductUnit
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simple-catalog", tags=["simple-catalog"])


def _default_location(db: Session) -> models.Location:
    settings = get_settings()
    # Сначала пытаемся найти склад с ID из настроек
    loc = db.query(models.Location).filter(models.Location.id == settings.default_location_id).first()
    if loc:
        return loc

    # Если склад с заданным ID не найден, пробуем найти по имени
    loc = db.query(models.Location).filter(models.Location.name == settings.default_location_name).first()
    if loc:
        return loc

    # Если ни по ID, ни по имени не найден, используем первый склад
    loc = db.query(models.Location).first()
    if not loc:
        # Если вообще нет складов, создаем первый
        loc = models.Location(name=settings.default_location_name, kind="warehouse")
        db.add(loc)
        db.flush()
    return loc


# Units
@router.get("/units/", response_model=List[schemas.Unit])
def get_units(user=Depends(PermissionChecker(["unit.read"])), db: Session = Depends(get_db)):
    units = db.query(models.Unit).all()
    return [
        schemas.Unit(
            id=u.id,
            code=u.code,
            description=u.description,
            unit_type=u.unit_type,
            is_discrete=u.is_discrete
        )
        for u in units
    ]


@router.post("/units/", response_model=schemas.Unit)
def create_unit(unit: schemas.UnitCreate, user=Depends(PermissionChecker(["unit.write"])), db: Session = Depends(get_db)):
    # Check if unit with this code already exists
    existing_unit = db.query(models.Unit).filter(models.Unit.code == unit.code).first()
    if existing_unit:
        raise HTTPException(status_code=400, detail="Unit with this code already exists")

    db_unit = models.Unit(
        code=unit.code,
        description=unit.description,
        unit_type=unit.unit_type or "base",  # Use provided value or default to base
        is_discrete=unit.is_discrete if unit.is_discrete is not None else True   # Use provided value or default to True
    )
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return schemas.Unit(
        id=db_unit.id,
        code=db_unit.code,
        description=db_unit.description,
        unit_type=db_unit.unit_type,
        is_discrete=db_unit.is_discrete
    )


# Product types
@router.get("/product-types/", response_model=List[schemas.ProductType])
def get_product_types(user=Depends(PermissionChecker(["product_type.read"])), db: Session = Depends(get_db)):
    types = db.query(models.ProductType).all()
    result = []
    for t in types:
        attrs = db.query(models.AttributeDefinition).filter(models.AttributeDefinition.product_type_id == t.id).all()
        result.append(
            schemas.ProductType(
                id=t.id,
                name=t.name,
                description=t.description,
                is_composite=t.is_composite,
                attributes=attrs,
            )
        )
    return result


@router.get("/product-types/{product_type_id}", response_model=schemas.ProductType)
def get_product_type(product_type_id: int, user=Depends(PermissionChecker(["product_type.read"])), db: Session = Depends(get_db)):
    t = db.query(models.ProductType).get(product_type_id)
    if not t:
        raise HTTPException(status_code=404, detail="Product type not found")
    attrs = db.query(models.AttributeDefinition).filter(models.AttributeDefinition.product_type_id == t.id).all()
    return schemas.ProductType(id=t.id, name=t.name, description=t.description, is_composite=t.is_composite, attributes=attrs)


@router.post("/product-types/", response_model=schemas.ProductType)
def create_product_type(payload: schemas.ProductTypeCreate, user=Depends(PermissionChecker(["product_type.write"])), db: Session = Depends(get_db)):
    t = models.ProductType(name=payload.name, description=payload.description, is_composite=payload.is_composite)
    db.add(t)
    db.flush()  # Get the ID before committing

    # Create attributes if provided
    created_attributes = []
    if hasattr(payload, 'attributes') and payload.attributes:
        for attr_data in payload.attributes:
            unit_id = None
            if attr_data.unit_code:
                unit = db.query(models.Unit).filter(models.Unit.code == attr_data.unit_code).first()
                if unit:
                    unit_id = unit.id

            attr = models.AttributeDefinition(
                product_type_id=t.id,
                name=attr_data.name,
                code=attr_data.code,
                data_type=attr_data.data_type,
                unit_id=unit_id,
                is_required=attr_data.is_required
            )
            db.add(attr)
            db.flush()
            created_attributes.append(attr)

    db.commit()
    db.refresh(t)

    # Refresh attributes
    for attr in created_attributes:
        db.refresh(attr)

    # Get all attributes for this product type
    attrs = db.query(models.AttributeDefinition).filter(models.AttributeDefinition.product_type_id == t.id).all()

    return schemas.ProductType(
        id=t.id,
        name=t.name,
        description=t.description,
        is_composite=t.is_composite,
        attributes=attrs
    )


@router.put("/product-types/{product_type_id}", response_model=schemas.ProductType)
def update_product_type(product_type_id: int, payload: schemas.ProductTypeUpdate, user=Depends(PermissionChecker(["product_type.write"])), db: Session = Depends(get_db)):
    t = db.query(models.ProductType).get(product_type_id)
    if not t:
        raise HTTPException(status_code=404, detail="Product type not found")

    # Update basic fields
    t.name = payload.name
    t.description = payload.description
    t.is_composite = payload.is_composite

    # Delete existing attribute values first to avoid foreign key constraint violations
    # Get the attribute definition IDs that will be deleted
    attr_def_ids = db.query(models.AttributeDefinition.id).filter(
        models.AttributeDefinition.product_type_id == product_type_id
    ).all()

    if attr_def_ids:
        attr_def_id_list = [row[0] for row in attr_def_ids]
        # Delete associated product attribute values
        db.query(models.ProductAttributeValue).filter(
            models.ProductAttributeValue.attribute_definition_id.in_(attr_def_id_list)
        ).delete()

    # Now delete the attribute definitions
    db.query(models.AttributeDefinition).filter(
        models.AttributeDefinition.product_type_id == product_type_id
    ).delete()

    # Create new attributes
    created_attributes = []
    if hasattr(payload, 'attributes') and payload.attributes:
        for attr_data in payload.attributes:
            unit_id = None
            if attr_data.unit_code:
                unit = db.query(models.Unit).filter(models.Unit.code == attr_data.unit_code).first()
                if unit:
                    unit_id = unit.id

            attr = models.AttributeDefinition(
                product_type_id=product_type_id,
                name=attr_data.name,
                code=attr_data.code,
                data_type=attr_data.data_type,
                unit_id=unit_id,
                is_required=attr_data.is_required
            )
            db.add(attr)
            db.flush()
            created_attributes.append(attr)

    db.commit()
    db.refresh(t)

    # Refresh attributes
    for attr in created_attributes:
        db.refresh(attr)

    # Get all attributes for this product type
    attrs = db.query(models.AttributeDefinition).filter(models.AttributeDefinition.product_type_id == t.id).all()

    return schemas.ProductType(
        id=t.id,
        name=t.name,
        description=t.description,
        is_composite=t.is_composite,
        attributes=attrs
    )


@router.delete("/product-types/{product_type_id}")
def delete_product_type(product_type_id: int, user=Depends(PermissionChecker(["product_type.delete"])), db: Session = Depends(get_db)):
    t = db.query(models.ProductType).get(product_type_id)
    if not t:
        raise HTTPException(status_code=404, detail="Product type not found")

    # Delete associated attributes
    db.query(models.AttributeDefinition).filter(
        models.AttributeDefinition.product_type_id == product_type_id
    ).delete()

    # Delete the product type
    db.delete(t)
    db.commit()
    return {"message": "Product type deleted successfully"}


# Attribute definitions
@router.post("/attribute-definitions/", response_model=schemas.AttributeDefinition)
def create_attribute_definition(attr_def: schemas.AttributeDefinitionCreate, user=Depends(PermissionChecker(["attribute_definition.write"])), db: Session = Depends(get_db)):
    unit_id = None
    if attr_def.unit_code:
        unit = db.query(models.Unit).filter(models.Unit.code == attr_def.unit_code).first()
        if unit:
            unit_id = unit.id

    db_def = models.AttributeDefinition(
        product_type_id=attr_def.product_type_id,
        name=attr_def.name,
        code=attr_def.code,
        data_type=attr_def.data_type,
        unit_id=unit_id,
        is_required=attr_def.is_required,
    )
    db.add(db_def)
    db.commit()
    db.refresh(db_def)
    return db_def


def _serialize_product(db_product: models.Product, db: Session) -> schemas.Product:
    # Собираем атрибуты как список с единым полем "value"
    attributes = []
    for attr in db_product.attributes:
        if attr.value_number is not None:
            val = attr.value_number
        elif attr.value_boolean is not None:
            val = attr.value_boolean
        elif attr.value_string is not None:
            val = attr.value_string
        else:
            val = None

        if val is not None:
            attributes.append(
                schemas.ProductAttributeValueCreate(
                    attribute_definition_id=attr.attribute_definition_id,
                    value=val
                )
            )

    components = [
        {"component_product_id": c.component_product_id, "quantity": c.quantity}
        for c in db_product.components
    ]

    # Calculate total stock across all locations for this product
    total_stock_result = (
        db.query(func.coalesce(func.sum(models.Stock.quantity), Decimal("0")))
        .filter(models.Stock.product_id == db_product.id)
        .scalar()
    )
    total_stock = total_stock_result if total_stock_result is not None else Decimal("0")

    return schemas.Product(
        id=db_product.id,
        product_type_id=db_product.product_type_id,
        name=db_product.name,
        unit_cost=db_product.unit_cost or Decimal("0"),
        stock=total_stock,
        is_composite=db_product.product_type.is_composite,
        base_unit_id=db_product.base_unit_id,
        attributes=attributes,  # ← список объектов с полем "value"
        components=components,
    )


def _ensure_unit(code: str, db: Session) -> models.Unit:
    unit = db.query(models.Unit).filter(models.Unit.code == code).first()
    if not unit:
        unit = models.Unit(
            code=code,
            description=code,
            unit_type="base",  # Default to base unit type
            is_discrete=True   # Default to discrete
        )
        db.add(unit)
        db.flush()
    return unit


# Products
@router.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, user=Depends(PermissionChecker(["product.write"])), db: Session = Depends(get_db)):
    # Get the base unit by ID
    base_unit = db.query(models.Unit).get(product.base_unit_id)
    if not base_unit:
        raise HTTPException(status_code=400, detail="Base unit not found")

    pt = db.query(models.ProductType).get(product.product_type_id)
    if not pt:
        raise HTTPException(status_code=400, detail="Product type not found")

    db_product = models.Product(
        product_type_id=product.product_type_id,
        name=product.name,
        sku=product.sku or product.name.replace(" ", "_"),
        primary_category=pt.name,
        base_unit_id=product.base_unit_id,
        unit_cost=product.unit_cost,
        is_active=True,
    )
    db.add(db_product)
    db.flush()

    # Атрибуты
    for attr in product.attributes:
        attr_def = db.get(AttributeDefinition, attr.attribute_definition_id)
        if not attr_def:
            raise ValueError("Invalid attribute definition")

        db_attr = ProductAttributeValue(
            product_id=db_product.id,  # ✅ ПРАВИЛЬНО: используем id сохранённого товара
            attribute_definition_id=attr.attribute_definition_id
        )

        if attr_def.data_type == "number":
            db_attr.value_number = float(attr.value) if attr.value is not None else None
        elif attr_def.data_type == "boolean":
            db_attr.value_boolean = bool(attr.value) if attr.value is not None else None
        elif attr_def.data_type == "string":
            db_attr.value_string = str(attr.value) if attr.value is not None else None

        db.add(db_attr)

    # Create product_unit entry for the base unit with ratio 1.0
    base_product_unit = models.ProductUnit(
        product_id=db_product.id,
        unit_id=product.base_unit_id,
        ratio_to_base=Decimal("1.0"),  # Base unit always has ratio 1.0
        discrete_step=None  # Default discrete step
    )
    db.add(base_product_unit)

    # Also add other units that might be commonly used with this product
    # For example, if the base unit is a bottle, we might want to add glass units
    # This would typically be done based on business rules or user input

    # Компоненты (если составной)
    if pt.is_composite:
        for comp in product.components:
            db_comp = models.CompositeComponent(
                parent_product_id=db_product.id,
                component_product_id=comp.component_product_id,
                quantity=Decimal(str(comp.quantity)),
                unit_id=product.base_unit_id,  # Changed to unit_id
            )
            db.add(db_comp)

    # Складской остаток
    loc = _default_location(db)
    stock = models.Stock(
        location_id=loc.id,
        product_id=db_product.id,  # ✅ тоже используем db_product.id
        quantity=Decimal(str(product.stock)),
        unit_id=product.base_unit_id,  # Changed to unit_id
    )
    db.add(stock)

    db.commit()
    db.refresh(db_product)
    return _serialize_product(db_product, db)


@router.get("/products/", response_model=List[schemas.Product])
def get_products(
    location_id: Optional[int] = None,
    product_type_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    user=Depends(PermissionChecker(["product.read"])),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product)

    if product_type_id:
        query = query.filter(models.Product.product_type_id == product_type_id)

    # Apply location filter if specified
    if location_id:
        # Subquery to get product IDs that have stock at the specified location
        subquery = (
            db.query(models.Stock.product_id)
            .filter(models.Stock.location_id == location_id)
            .distinct()
        )
        query = query.filter(models.Product.id.in_(subquery))

    products = query.offset(skip).limit(limit).all()
    return [_serialize_product(p, db) for p in products]


@router.get("/products-count/")
def get_products_count(
    location_id: Optional[int] = None,
    product_type_id: Optional[int] = None,
    user=Depends(PermissionChecker(["product.read"])),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product)

    if product_type_id:
        query = query.filter(models.Product.product_type_id == product_type_id)

    if location_id:
        # Subquery to get product IDs that have stock at the specified location
        subquery = (
            db.query(models.Stock.product_id)
            .filter(models.Stock.location_id == location_id)
            .distinct()
        )
        query = query.filter(models.Product.id.in_(subquery))

    count = query.count()
    return {"count": count}


@router.get("/products/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, user=Depends(PermissionChecker(["product.read"])), db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _serialize_product(product, db)


@router.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product_update: schemas.ProductUpdate, user=Depends(PermissionChecker(["product.write"])), db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Ensure base_unit_id is provided or use existing value
    base_unit_id = product_update.base_unit_id
    if base_unit_id is None:
        # Use the existing base_unit_id from the product
        base_unit_id = product.base_unit_id

    # Get the base unit by ID
    base_unit = db.query(models.Unit).get(base_unit_id)
    if not base_unit:
        raise HTTPException(status_code=400, detail="Base unit not found")

    pt = db.query(models.ProductType).get(product_update.product_type_id)
    if not pt:
        raise HTTPException(status_code=400, detail="Product type not found")

    product.product_type_id = product_update.product_type_id
    product.name = product_update.name
    product.unit_cost = product_update.unit_cost
    # Always update base_unit_id with the resolved value
    product.base_unit_id = base_unit_id

    db.query(models.ProductAttributeValue).filter(models.ProductAttributeValue.product_id == product.id).delete()
    for attr in product_update.attributes:
        attr_def = db.get(AttributeDefinition, attr.attribute_definition_id)
        if not attr_def:
            raise ValueError("Invalid attribute definition")

        db_attr = models.ProductAttributeValue(
            product_id=product.id,
            attribute_definition_id=attr.attribute_definition_id
        )

        if attr_def.data_type == "number":
            db_attr.value_number = float(attr.value) if attr.value is not None else None
        elif attr_def.data_type == "boolean":
            db_attr.value_boolean = bool(attr.value) if attr.value is not None else None
        elif attr_def.data_type == "string":
            db_attr.value_string = str(attr.value) if attr.value is not None else None

        db.add(db_attr)

    # Update product_unit entry for the base unit with ratio 1.0
    # First, check if there's already a product_unit entry for the base unit
    existing_base_unit = db.query(models.ProductUnit).filter(
        models.ProductUnit.product_id == product.id,
        models.ProductUnit.unit_id == base_unit_id
    ).first()

    if existing_base_unit:
        # Update the existing base unit entry
        existing_base_unit.ratio_to_base = Decimal("1.0")
    else:
        # Create a new product_unit entry for the base unit
        base_product_unit = models.ProductUnit(
            product_id=product.id,
            unit_id=base_unit_id,
            ratio_to_base=Decimal("1.0"),  # Base unit always has ratio 1.0
            discrete_step=None  # Default discrete step
        )
        db.add(base_product_unit)

    db.query(models.CompositeComponent).filter(models.CompositeComponent.parent_product_id == product.id).delete()
    if pt.is_composite:
        for comp in product_update.components:
            db_comp = models.CompositeComponent(
                parent_product_id=product.id,
                component_product_id=comp.component_product_id,
                quantity=Decimal(str(comp.quantity)),
                unit_id=base_unit_id,  # Changed to unit_id
            )
            db.add(db_comp)

    loc = _default_location(db)
    stock = (
        db.query(models.Stock)
        .filter(models.Stock.location_id == loc.id, models.Stock.product_id == product.id)
        .first()
    )
    if stock:
        stock.quantity = Decimal(str(product_update.stock))
        stock.unit_id = base_unit_id
    else:
        db.add(
            models.Stock(
                location_id=loc.id,
                product_id=product.id,
                quantity=Decimal(str(product_update.stock)),
                unit_id=base_unit_id,
            )
        )
    db.commit()
    db.refresh(product)
    return _serialize_product(product, db)


@router.delete("/products/{product_id}")
def delete_product(product_id: int, user=Depends(PermissionChecker(["product.delete"])), db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.query(models.ProductAttributeValue).filter(models.ProductAttributeValue.product_id == product.id).delete()
    db.query(models.CompositeComponent).filter(models.CompositeComponent.parent_product_id == product.id).delete()
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}



# Unit Conversions
@router.get("/unit-conversions/", response_model=List[schemas.UnitConversionSchema])
def get_unit_conversions(user=Depends(PermissionChecker(["unit_conversion.read"])), db: Session = Depends(get_db)):
    logger.warning("UnitConversion API is deprecated. Use ProductUnit for product-specific conversions.")
    # Return empty list since UnitConversion table no longer exists
    return []


@router.post("/unit-conversions/", response_model=schemas.UnitConversionSchema)
def create_unit_conversion(conversion: schemas.UnitConversionSchema, user=Depends(PermissionChecker(["unit_conversion.write"])), db: Session = Depends(get_db)):
    logger.error("UnitConversion API is deprecated. Use ProductUnit for product-specific conversions.")
    # Raise an error since UnitConversion table no longer exists
    raise HTTPException(status_code=400, detail="UnitConversion API is deprecated. Use ProductUnit for product-specific conversions.")


# Locations
@router.get("/locations/", response_model=List[schemas.Location])
def get_locations(user=Depends(PermissionChecker(["location.read"])), db: Session = Depends(get_db)):
    locations = db.query(models.Location).all()
    return [
        schemas.Location(
            id=l.id,
            name=l.name,
            kind=l.kind,
        )
        for l in locations
    ]


@router.post("/locations/", response_model=schemas.Location)
def create_location(location: schemas.LocationBase, user=Depends(PermissionChecker(["location.write"])), db: Session = Depends(get_db)):
    db_location = models.Location(name=location.name, kind=location.kind)
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return schemas.Location(
        id=db_location.id,
        name=db_location.name,
        kind=db_location.kind,
    )


@router.post("/sales/")
def sell_product(sale_request: schemas.SaleRequest, user=Depends(PermissionChecker(["sale.write"])), db: Session = Depends(get_db)):
    product = db.query(models.Product).get(sale_request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    loc = _default_location(db)
    stock = (
        db.query(models.Stock)
        .filter(models.Stock.location_id == loc.id, models.Stock.product_id == product.id)
        .with_for_update()
        .first()
    )
    if not stock or stock.quantity < sale_request.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    if product.product_type.is_composite:
        components = db.query(models.CompositeComponent).filter(models.CompositeComponent.parent_product_id == product.id).all()
        for comp in components:
            comp_stock = (
                db.query(models.Stock)
                .filter(models.Stock.location_id == loc.id, models.Stock.product_id == comp.component_product_id)
                .with_for_update()
                .first()
            )
            required = Decimal(str(comp.quantity)) * sale_request.quantity
            if not comp_stock or comp_stock.quantity < required:
                raise HTTPException(status_code=400, detail="Insufficient stock for component")
            comp_stock.quantity -= required
    stock.quantity -= sale_request.quantity
    db.commit()
    return {"message": f"Successfully sold {sale_request.quantity} of {product.name}"}


@router.post("/glass-sales/")
def sell_wine_glass(sale_request: schemas.SaleRequest, user=Depends(PermissionChecker(["sale.write"])), db: Session = Depends(get_db)):
    product = db.query(models.Product).get(sale_request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    glasses_per_bottle = (
        db.query(models.ProductAttributeValue)
        .join(models.AttributeDefinition, models.ProductAttributeValue.attribute_definition_id == models.AttributeDefinition.id)
        .filter(
            models.ProductAttributeValue.product_id == product.id,
            models.AttributeDefinition.code == "glasses_per_bottle",
        )
        .first()
    )
    if not glasses_per_bottle or not glasses_per_bottle.value_number:
        raise HTTPException(status_code=400, detail="Missing glasses_per_bottle")
    bottles_needed = sale_request.quantity / glasses_per_bottle.value_number

    loc = _default_location(db)
    stock = (
        db.query(models.Stock)
        .filter(models.Stock.location_id == loc.id, models.Stock.product_id == product.id)
        .with_for_update()
        .first()
    )
    if not stock or stock.quantity < bottles_needed:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    stock.quantity -= bottles_needed
    db.commit()
    return {"message": f"Successfully sold {sale_request.quantity} glasses of {product.name}"}


# Unit management endpoints
@router.put("/units/{unit_id}", response_model=schemas.Unit)
def update_unit(unit_id: int, unit_update: schemas.UnitUpdate, user=Depends(PermissionChecker(["unit.write"])), db: Session = Depends(get_db)):
    db_unit = db.query(models.Unit).get(unit_id)
    if not db_unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Check if another unit with this code already exists (excluding current unit)
    existing_unit = db.query(models.Unit).filter(
        models.Unit.code == unit_update.code,
        models.Unit.id != unit_id
    ).first()
    if existing_unit:
        raise HTTPException(status_code=400, detail="Unit with this code already exists")

    # Update fields
    db_unit.code = unit_update.code
    db_unit.description = unit_update.description
    db_unit.unit_type = unit_update.unit_type
    db_unit.is_discrete = unit_update.is_discrete

    db.commit()
    db.refresh(db_unit)
    return schemas.Unit(
        id=db_unit.id,
        code=db_unit.code,
        description=db_unit.description,
        unit_type=db_unit.unit_type,
        is_discrete=db_unit.is_discrete
    )


@router.delete("/units/{unit_id}")
def delete_unit(unit_id: int, user=Depends(PermissionChecker(["unit.delete"])), db: Session = Depends(get_db)):
    db_unit = db.query(models.Unit).get(unit_id)
    if not db_unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Check if unit is used by other entities to prevent foreign key constraint violations
    # Check specific tables that reference units
    from app.models.models import ProductUnit, Stock, PriceList, Adjustment, Transfer, SaleLine, AttributeDefinition, CompositeComponent

    # Check if this unit is referenced in ProductUnit
    product_unit_count = db.query(ProductUnit).filter(ProductUnit.unit_id == unit_id).count()
    if product_unit_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by product units")

    # Check if this unit is referenced in Stock
    stock_count = db.query(Stock).filter(Stock.unit_id == unit_id).count()
    if stock_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by stock records")

    # Check if this unit is referenced in PriceList
    price_list_count = db.query(PriceList).filter(PriceList.unit_id == unit_id).count()
    if price_list_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by price lists")

    # Check if this unit is referenced in Adjustment
    adjustment_count = db.query(Adjustment).filter(Adjustment.unit_id == unit_id).count()
    if adjustment_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by adjustments")

    # Check if this unit is referenced in Transfer
    transfer_count = db.query(Transfer).filter(Transfer.unit_id == unit_id).count()
    if transfer_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by transfers")

    # Check if this unit is referenced in SaleLine
    sale_line_count = db.query(SaleLine).filter(SaleLine.unit_id == unit_id).count()
    if sale_line_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by sale lines")

    # Check if this unit is referenced in AttributeDefinition
    attr_def_count = db.query(AttributeDefinition).filter(AttributeDefinition.unit_id == unit_id).count()
    if attr_def_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by attribute definitions")

    # Check if this unit is referenced in CompositeComponent
    comp_count = db.query(CompositeComponent).filter(CompositeComponent.unit_id == unit_id).count()
    if comp_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete unit: it is referenced by composite components")

    db.delete(db_unit)
    db.commit()
    return {"message": "Unit deleted successfully"}
