from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db
from app.models import models
from app.schemas import simple as schemas

from app.models.models import AttributeDefinition, ProductAttributeValue

router = APIRouter(prefix="/simple-catalog", tags=["simple-catalog"])


def _default_location(db: Session) -> models.Location:
    loc = db.query(models.Location).first()
    if not loc:
        loc = models.Location(name="Default", kind="default")
        db.add(loc)
        db.flush()
    return loc


# Units
@router.get("/units/", response_model=List[schemas.Unit])
def get_units(db: Session = Depends(get_db)):
    units = db.query(models.Unit).all()
    return [
        schemas.Unit(
            code=u.code,
            symbol=u.code,
            name=u.description,
            base_unit_code=None,
            conversion_factor=u.ratio_to_base,
        )
        for u in units
    ]


@router.post("/units/", response_model=schemas.Unit)
def create_unit(unit: schemas.UnitCreate, db: Session = Depends(get_db)):
    db_unit = models.Unit(code=unit.symbol, description=unit.name, ratio_to_base=unit.conversion_factor or 1)
    db.add(db_unit)
    db.flush()
    if unit.base_unit_code and unit.conversion_factor:
        conv = models.UnitConversion(from_unit=unit.symbol, to_unit=unit.base_unit_code, ratio=unit.conversion_factor)
        db.add(conv)
    db.commit()
    db.refresh(db_unit)
    return schemas.Unit(
        code=db_unit.code,
        symbol=db_unit.code,
        name=db_unit.description,
        base_unit_code=unit.base_unit_code,
        conversion_factor=db_unit.ratio_to_base,
    )


# Product types
@router.get("/product-types/", response_model=List[schemas.ProductType])
def get_product_types(db: Session = Depends(get_db)):
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
def get_product_type(product_type_id: int, db: Session = Depends(get_db)):
    t = db.query(models.ProductType).get(product_type_id)
    if not t:
        raise HTTPException(status_code=404, detail="Product type not found")
    attrs = db.query(models.AttributeDefinition).filter(models.AttributeDefinition.product_type_id == t.id).all()
    return schemas.ProductType(id=t.id, name=t.name, description=t.description, is_composite=t.is_composite, attributes=attrs)


@router.post("/product-types/", response_model=schemas.ProductType)
def create_product_type(payload: schemas.ProductTypeCreate, db: Session = Depends(get_db)):
    t = models.ProductType(name=payload.name, description=payload.description, is_composite=payload.is_composite)
    db.add(t)
    db.commit()
    db.refresh(t)
    return schemas.ProductType(id=t.id, name=t.name, description=t.description, is_composite=t.is_composite, attributes=[])


# Attribute definitions
@router.post("/attribute-definitions/", response_model=schemas.AttributeDefinition)
def create_attribute_definition(attr_def: schemas.AttributeDefinitionCreate, db: Session = Depends(get_db)):
    db_def = models.AttributeDefinition(
        product_type_id=attr_def.product_type_id,
        name=attr_def.name,
        code=attr_def.code,
        data_type=attr_def.data_type,
        unit_code=attr_def.unit_code,
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

    # Stock logic (оставьте как есть)
    loc = _default_location(db)
    stock_row = db.query(models.Stock).filter(
        models.Stock.location_id == loc.id,
        models.Stock.product_id == db_product.id
    ).first()
    stock_qty = stock_row.quantity if stock_row else Decimal("0")

    return schemas.Product(
        id=db_product.id,
        product_type_id=db_product.product_type_id,
        name=db_product.name,
        unit_cost=db_product.unit_cost or Decimal("0"),
        stock=stock_qty,
        is_composite=db_product.is_composite,
        attributes=attributes,  # ← список объектов с полем "value"
        components=components,
    )


def _ensure_unit(code: str, db: Session) -> models.Unit:
    unit = db.query(models.Unit).get(code)
    if not unit:
        unit = models.Unit(code=code, description=code)
        db.add(unit)
        db.flush()
    return unit


# Products
@router.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    base_unit = product.base_unit_code or "unit"
    _ensure_unit(base_unit, db)
    pt = db.query(models.ProductType).get(product.product_type_id)
    if not pt:
        raise HTTPException(status_code=400, detail="Product type not found")
    db_product = models.Product(
        product_type_id=product.product_type_id,
        name=product.name,
        sku=product.sku or product.name.replace(" ", "_"),
        primary_category=pt.name,
        base_unit_code=base_unit,
        unit_cost=product.unit_cost,
        is_composite=pt.is_composite,
        is_active=True,
    )
    db.add(db_product)
    db.flush()

    for attr in product.attributes:
        attr_def = db.get(AttributeDefinition, attr.attribute_definition_id)
        if not attr_def:
            raise ValueError("Invalid attribute definition")

        db_attr = ProductAttributeValue(
            product_id=product.id,
            attribute_definition_id=attr.attribute_definition_id
        )

        if attr_def.data_type == "number":
            db_attr.value_number = attr.value
        elif attr_def.data_type == "boolean":
            db_attr.value_boolean = attr.value
        elif attr_def.data_type == "string":
            db_attr.value_string = attr.value

        db.add(db_attr)

    if pt.is_composite:
        for comp in product.components:
            db_comp = models.CompositeComponent(
                parent_product_id=db_product.id,
                component_product_id=comp.component_product_id,
                quantity=Decimal(str(comp.quantity)),
                unit_code=base_unit,
            )
            db.add(db_comp)

    loc = _default_location(db)
    stock = models.Stock(
        location_id=loc.id,
        product_id=db_product.id,
        quantity=Decimal(str(product.stock)),
        unit_code=base_unit,
    )
    db.add(stock)
    db.commit()
    db.refresh(db_product)
    return _serialize_product(db_product, db)


@router.get("/products/", response_model=List[schemas.Product])
def get_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return [_serialize_product(p, db) for p in products]


@router.get("/products/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _serialize_product(product, db)


@router.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product_update: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    base_unit = product_update.base_unit_code or product.base_unit_code
    _ensure_unit(base_unit, db)
    pt = db.query(models.ProductType).get(product_update.product_type_id)
    if not pt:
        raise HTTPException(status_code=400, detail="Product type not found")

    product.product_type_id = product_update.product_type_id
    product.name = product_update.name
    product.unit_cost = product_update.unit_cost
    product.is_composite = pt.is_composite
    product.base_unit_code = base_unit

    db.query(models.ProductAttributeValue).filter(models.ProductAttributeValue.product_id == product.id).delete()
    for attr in product_update.attributes:
        db_attr = models.ProductAttributeValue(
            product_id=product.id,
            attribute_definition_id=attr.attribute_definition_id,
            value_number=Decimal(str(attr.value)) if isinstance(attr.value, (int, float, Decimal)) else None,
            value_boolean=bool(attr.value) if isinstance(attr.value, bool) else None,
            value_string=str(attr.value) if isinstance(attr.value, str) else None,
        )
        db.add(db_attr)

    db.query(models.CompositeComponent).filter(models.CompositeComponent.parent_product_id == product.id).delete()
    if pt.is_composite:
        for comp in product_update.components:
            db_comp = models.CompositeComponent(
                parent_product_id=product.id,
                component_product_id=comp.component_product_id,
                quantity=Decimal(str(comp.quantity)),
                unit_code=base_unit,
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
    else:
        db.add(
            models.Stock(
                location_id=loc.id,
                product_id=product.id,
                quantity=Decimal(str(product_update.stock)),
                unit_code=base_unit,
            )
        )
    db.commit()
    db.refresh(product)
    return _serialize_product(product, db)


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.query(models.ProductAttributeValue).filter(models.ProductAttributeValue.product_id == product.id).delete()
    db.query(models.CompositeComponent).filter(models.CompositeComponent.parent_product_id == product.id).delete()
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}


@router.post("/sales/")
def sell_product(sale_request: schemas.SaleRequest, db: Session = Depends(get_db)):
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

    if product.is_composite:
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
def sell_wine_glass(sale_request: schemas.SaleRequest, db: Session = Depends(get_db)):
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
