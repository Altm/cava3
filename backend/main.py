from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, schemas, database
from typing import List

app = FastAPI(title="Product Catalog API")

@app.on_event("startup")
async def startup():
    database.init_db()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Product Types ---
@app.get("/product-types/", response_model=List[schemas.ProductType])
def get_product_types(db: Session = Depends(get_db)):
    return db.query(models.ProductType).all()

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
    product_type = db.query(models.ProductType).get(product.product_type_id)
    if product_type.is_composite:
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
        comps = [{"component_product_id": c.component_product_id, "quantity": c.quantity} for c in p.components]
        result.append({
            "id": p.id,
            "product_type_id": p.product_type_id,
            "name": p.name,
            "stock": p.stock,
            "unit_cost": p.unit_cost,
            "is_composite": p.is_composite,
            "attributes": attrs,
            "components": comps
        })
    return result