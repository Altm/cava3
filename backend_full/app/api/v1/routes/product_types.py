from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from app.api.v1.deps.auth import get_db, get_current_user, check_permission
from app.models.models import ProductType, AttributeDefinition
from app.schemas.product_schemas import ProductType as ProductTypeSchema, ProductTypeBase, AttributeDefinition as AttributeDefinitionSchema, AttributeDefinitionBase
from typing import List

router = APIRouter(prefix="/product-types", tags=["product-types"])


@router.get("", response_model=List[ProductTypeSchema])
def list_product_types(db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.read", db=db)
    product_types = db.query(ProductType).options(
        joinedload(ProductType.attributes)
    ).all()
    
    result = []
    for pt in product_types:
        result.append(ProductTypeSchema(
            id=pt.id,
            name=pt.name,
            description=pt.description,
            is_composite=pt.is_composite,
            attributes=pt.attributes
        ))
    
    return result


@router.get("/{product_type_id}", response_model=ProductTypeSchema)
def get_product_type(product_type_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.read", db=db)
    product_type = db.query(ProductType).options(
        joinedload(ProductType.attributes)
    ).filter(ProductType.id == product_type_id).first()
    
    if not product_type:
        raise HTTPException(status_code=404, detail="Product type not found")
    
    return ProductTypeSchema(
        id=product_type.id,
        name=product_type.name,
        description=product_type.description,
        is_composite=product_type.is_composite,
        attributes=product_type.attributes
    )


@router.post("", response_model=ProductTypeSchema)
def create_product_type(product_type_create: ProductTypeBase, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    
    # Check if product type with same name already exists
    existing = db.query(ProductType).filter(ProductType.name == product_type_create.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product type with this name already exists")
    
    db_product_type = ProductType(
        name=product_type_create.name,
        description=product_type_create.description,
        is_composite=product_type_create.is_composite
    )
    db.add(db_product_type)
    db.commit()
    db.refresh(db_product_type)
    
    # Return with attributes (empty initially)
    return ProductTypeSchema(
        id=db_product_type.id,
        name=db_product_type.name,
        description=db_product_type.description,
        is_composite=db_product_type.is_composite,
        attributes=[]
    )


@router.put("/{product_type_id}", response_model=ProductTypeSchema)
def update_product_type(product_type_id: int, product_type_update: ProductTypeBase, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    product_type = db.query(ProductType).filter(ProductType.id == product_type_id).first()
    if not product_type:
        raise HTTPException(status_code=404, detail="Product type not found")
    
    # Update fields
    product_type.name = product_type_update.name
    product_type.description = product_type_update.description
    product_type.is_composite = product_type_update.is_composite
    
    db.commit()
    db.refresh(product_type)
    
    # Return with attributes
    return ProductTypeSchema(
        id=product_type.id,
        name=product_type.name,
        description=product_type.description,
        is_composite=product_type.is_composite,
        attributes=product_type.attributes
    )


@router.delete("/{product_type_id}")
def delete_product_type(product_type_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    product_type = db.query(ProductType).filter(ProductType.id == product_type_id).first()
    if not product_type:
        raise HTTPException(status_code=404, detail="Product type not found")
    
    # Check if any products exist with this type
    from app.models.models import Product
    product_count = db.query(Product).filter(Product.product_type_id == product_type_id).count()
    if product_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete product type with associated products")
    
    db.delete(product_type)
    db.commit()
    return {"message": "Product type deleted successfully"}