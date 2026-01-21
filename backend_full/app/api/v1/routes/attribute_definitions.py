from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db, get_current_user, check_permission
from app.models.models import AttributeDefinition, ProductType
from app.schemas.product_schemas import AttributeDefinition as AttributeDefinitionSchema, AttributeDefinitionBase
from typing import List

router = APIRouter(prefix="/attribute-definitions", tags=["attribute-definitions"])


@router.get("", response_model=List[AttributeDefinitionSchema])
def list_attribute_definitions(db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.read", db=db)
    attribute_definitions = db.query(AttributeDefinition).all()
    return attribute_definitions


@router.get("/{attribute_definition_id}", response_model=AttributeDefinitionSchema)
def get_attribute_definition(attribute_definition_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.read", db=db)
    attribute_definition = db.query(AttributeDefinition).filter(
        AttributeDefinition.id == attribute_definition_id
    ).first()
    
    if not attribute_definition:
        raise HTTPException(status_code=404, detail="Attribute definition not found")
    
    return attribute_definition


@router.post("", response_model=AttributeDefinitionSchema)
def create_attribute_definition(attr_def_create: AttributeDefinitionBase, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    
    # Check if product type exists
    product_type = db.query(ProductType).filter(ProductType.id == attr_def_create.product_type_id).first()
    if not product_type:
        raise HTTPException(status_code=404, detail="Product type not found")
    
    # Check if attribute definition with same code already exists for this product type
    existing = db.query(AttributeDefinition).filter(
        AttributeDefinition.product_type_id == attr_def_create.product_type_id,
        AttributeDefinition.code == attr_def_create.code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attribute definition with this code already exists for this product type")
    
    # Validate data type
    valid_data_types = ["number", "boolean", "string"]
    if attr_def_create.data_type.lower() not in valid_data_types:
        raise HTTPException(status_code=400, detail=f"data_type must be one of: {valid_data_types}")
    
    db_attr_def = AttributeDefinition(
        name=attr_def_create.name,
        code=attr_def_create.code,
        data_type=attr_def_create.data_type.lower(),
        unit_id=attr_def_create.unit_id,
        is_required=attr_def_create.is_required,
        product_type_id=attr_def_create.product_type_id
    )
    db.add(db_attr_def)
    db.commit()
    db.refresh(db_attr_def)
    
    return db_attr_def


@router.put("/{attribute_definition_id}", response_model=AttributeDefinitionSchema)
def update_attribute_definition(attribute_definition_id: int, attr_def_update: AttributeDefinitionBase, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    attr_def = db.query(AttributeDefinition).filter(AttributeDefinition.id == attribute_definition_id).first()
    if not attr_def:
        raise HTTPException(status_code=404, detail="Attribute definition not found")
    
    # Check if product type exists
    product_type = db.query(ProductType).filter(ProductType.id == attr_def_update.product_type_id).first()
    if not product_type:
        raise HTTPException(status_code=404, detail="Product type not found")
    
    # Check if attribute definition with same code already exists for this product type (excluding current one)
    existing = db.query(AttributeDefinition).filter(
        AttributeDefinition.product_type_id == attr_def_update.product_type_id,
        AttributeDefinition.code == attr_def_update.code,
        AttributeDefinition.id != attribute_definition_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attribute definition with this code already exists for this product type")
    
    # Validate data type
    valid_data_types = ["number", "boolean", "string"]
    if attr_def_update.data_type.lower() not in valid_data_types:
        raise HTTPException(status_code=400, detail=f"data_type must be one of: {valid_data_types}")
    
    # Update fields
    attr_def.name = attr_def_update.name
    attr_def.code = attr_def_update.code
    attr_def.data_type = attr_def_update.data_type.lower()
    attr_def.unit_id = attr_def_update.unit_id
    attr_def.is_required = attr_def_update.is_required
    attr_def.product_type_id = attr_def_update.product_type_id
    
    db.commit()
    db.refresh(attr_def)
    
    return attr_def


@router.delete("/{attribute_definition_id}")
def delete_attribute_definition(attribute_definition_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    attr_def = db.query(AttributeDefinition).filter(AttributeDefinition.id == attribute_definition_id).first()
    if not attr_def:
        raise HTTPException(status_code=404, detail="Attribute definition not found")
    
    # Check if any products have values for this attribute definition
    from app.models.models import ProductAttributeValue
    value_count = db.query(ProductAttributeValue).filter(
        ProductAttributeValue.attribute_definition_id == attribute_definition_id
    ).count()
    if value_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete attribute definition with associated values")
    
    db.delete(attr_def)
    db.commit()
    return {"message": "Attribute definition deleted successfully"}