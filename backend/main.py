from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import backend.models as models
import backend.schemas as schemas
import backend.database as database
from backend.init_sample_data import init_sample_data
from typing import List

app = FastAPI(title="Product Catalog API")

@app.on_event("startup")
async def startup():
    database.init_db()
    # Initialize sample data
    db = database.SessionLocal()
    try:
        # Check if sample data already exists
        product_count = db.query(models.Product).count()
        if product_count == 0:
            init_sample_data(db)
    finally:
        db.close()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Units ---
@app.get("/units/", response_model=List[schemas.Unit])
def get_units(db: Session = Depends(get_db)):
    return db.query(models.Unit).all()

@app.post("/units/", response_model=schemas.Unit)
def create_unit(unit: schemas.UnitBase, db: Session = Depends(get_db)):
    db_unit = models.Unit(**unit.model_dump())
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

# --- Product Types ---
@app.get("/product-types/", response_model=List[schemas.ProductType])
def get_product_types(db: Session = Depends(get_db)):
    product_types = db.query(models.ProductType).all()
    result = []
    for pt in product_types:
        attributes = db.query(models.AttributeDefinition).filter(
            models.AttributeDefinition.product_type_id == pt.id
        ).all()
        result.append({
            "id": pt.id,
            "name": pt.name,
            "is_composite": pt.is_composite,
            "attributes": attributes
        })
    return result

@app.post("/product-types/", response_model=schemas.ProductType)
def create_product_type(product_type: schemas.ProductTypeBase, db: Session = Depends(get_db)):
    db_product_type = models.ProductType(**product_type.model_dump())
    db.add(db_product_type)
    db.commit()
    db.refresh(db_product_type)
    
    # Return with attributes
    return {
        "id": db_product_type.id,
        "name": db_product_type.name,
        "is_composite": db_product_type.is_composite,
        "attributes": []
    }

# --- Attribute Definitions ---
@app.post("/attribute-definitions/", response_model=schemas.AttributeDefinition)
def create_attribute_definition(attr_def: schemas.AttributeDefinitionBase, db: Session = Depends(get_db)):
    db_attr_def = models.AttributeDefinition(**attr_def.model_dump())
    db.add(db_attr_def)
    db.commit()
    db.refresh(db_attr_def)
    return db_attr_def

# --- Products ---
@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    # Создаём товар
    db_product = models.Product(
        product_type_id=product.product_type_id,
        name=product.name,
        unit_cost=product.unit_cost,
        stock=product.stock
    )
    db.add(db_product)
    db.flush()

    # Атрибуты
    for attr in product.attributes:
        db_attr = models.ProductAttributeValue(
            product_id=db_product.id,
            attribute_definition_id=attr.attribute_definition_id,
            value_number=attr.value if isinstance(attr.value, (int, float)) else None,
            value_boolean=attr.value if isinstance(attr.value, bool) else None,
            value_string=str(attr.value) if isinstance(attr.value, str) else None
        )
        db.add(db_attr)

    # Компоненты (только для составных)
    product_type = db.query(models.ProductType).filter(models.ProductType.id == product.product_type_id).first()
    if product_type and product_type.is_composite:
        for comp in product.components:
            for comp_id, qty in comp.items():
                db_comp = models.ProductComponent(
                    composite_product_id=db_product.id,
                    component_product_id=int(comp_id),
                    quantity=qty
                )
                db.add(db_comp)

    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[schemas.Product])
def get_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    result = []
    for p in products:
        # Получаем атрибуты
        attrs = {}
        for av in p.attributes:
            defn = av.attribute_definition
            if defn.data_type == "number":
                val = av.value_number
            elif defn.data_type == "boolean":
                val = av.value_boolean
            else:
                val = av.value_string
            attrs[defn.code] = val
        
        # Получаем компоненты
        comps = [{"component_product_id": c.component_product_id, "quantity": c.quantity} for c in p.components]
        
        # Определяем, является ли товар составным
        is_composite = p.product_type.is_composite if p.product_type else False
        
        result.append({
            "id": p.id,
            "product_type_id": p.product_type_id,
            "name": p.name,
            "stock": p.stock,
            "unit_cost": p.unit_cost,
            "is_composite": is_composite,
            "attributes": attrs,
            "components": comps
        })
    return result

@app.get("/products/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Получаем атрибуты
    attrs = {}
    for av in product.attributes:
        defn = av.attribute_definition
        if defn.data_type == "number":
            val = av.value_number
        elif defn.data_type == "boolean":
            val = av.value_boolean
        else:
            val = av.value_string
        attrs[defn.code] = val
    
    # Получаем компоненты
    comps = [{"component_product_id": c.component_product_id, "quantity": c.quantity} for c in product.components]
    
    # Определяем, является ли товар составным
    is_composite = product.product_type.is_composite if product.product_type else False
    
    return {
        "id": product.id,
        "product_type_id": product.product_type_id,
        "name": product.name,
        "stock": product.stock,
        "unit_cost": product.unit_cost,
        "is_composite": is_composite,
        "attributes": attrs,
        "components": comps
    }

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product_update: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Обновляем основные поля
    product.product_type_id = product_update.product_type_id
    product.name = product_update.name
    product.unit_cost = product_update.unit_cost
    product.stock = product_update.stock
    
    # Удаляем старые атрибуты
    db.query(models.ProductAttributeValue).filter(
        models.ProductAttributeValue.product_id == product_id
    ).delete()
    
    # Добавляем новые атрибуты
    for attr in product_update.attributes:
        db_attr = models.ProductAttributeValue(
            product_id=product.id,
            attribute_definition_id=attr.attribute_definition_id,
            value_number=attr.value if isinstance(attr.value, (int, float)) else None,
            value_boolean=attr.value if isinstance(attr.value, bool) else None,
            value_string=str(attr.value) if isinstance(attr.value, str) else None
        )
        db.add(db_attr)

    # Удаляем старые компоненты
    db.query(models.ProductComponent).filter(
        models.ProductComponent.composite_product_id == product_id
    ).delete()
    
    # Добавляем новые компоненты (только для составных)
    product_type = db.query(models.ProductType).filter(models.ProductType.id == product_update.product_type_id).first()
    if product_type and product_type.is_composite:
        for comp in product_update.components:
            for comp_id, qty in comp.items():
                db_comp = models.ProductComponent(
                    composite_product_id=product.id,
                    component_product_id=int(comp_id),
                    quantity=qty
                )
                db.add(db_comp)

    db.commit()
    db.refresh(product)
    return product

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}
