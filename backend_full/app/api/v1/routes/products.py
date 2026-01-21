from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from app.api.v1.deps.auth import get_db, get_current_user, check_permission
from app.models.models import Product, ProductType, AttributeDefinition, ProductAttributeValue, CompositeComponent
from app.schemas.product_schemas import Product as ProductSchema, ProductCreate, ProductUpdate, ProductType as ProductTypeSchema, ProductTypeBase, AttributeDefinition as AttributeDefinitionSchema, AttributeDefinitionBase, ProductAttributeValueCreate, SaleRequest
from typing import List

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=List[ProductSchema])
def list_products(db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.read", db=db)
    products = db.query(Product).options(
        joinedload(Product.product_type),
        joinedload(Product.attributes).joinedload(ProductAttributeValue.attribute_definition),
        joinedload(Product.components).joinedload(CompositeComponent.component_product)
    ).all()
    
    result = []
    for p in products:
        # Get attributes
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
        
        # Get components
        comps = [{
            "component_product_id": c.component_product_id, 
            "quantity": float(c.quantity),
            "unit_code": c.unit_code,
            "substitution_allowed": c.substitution_allowed
        } for c in p.components]
        
        result.append(ProductSchema(
            id=p.id,
            name=p.name,
            sku=p.sku,
            primary_category=p.primary_category,
            product_type_id=p.product_type_id,
            base_unit_code=p.base_unit_code,
            is_composite=p.is_composite,
            is_active=p.is_active,
            tax_flags=p.tax_flags,
            unit_cost=p.unit_cost,
            attributes=attrs,
            components=comps
        ))
    
    return result


@router.get("/{product_id}", response_model=ProductSchema)
def get_product(product_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.read", db=db)
    product = db.query(Product).options(
        joinedload(Product.product_type),
        joinedload(Product.attributes).joinedload(ProductAttributeValue.attribute_definition),
        joinedload(Product.components).joinedload(CompositeComponent.component_product)
    ).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get attributes
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
    
    # Get components
    comps = [{
        "component_product_id": c.component_product_id, 
        "quantity": float(c.quantity),
        "unit_code": c.unit_code,
        "substitution_allowed": c.substitution_allowed
    } for c in product.components]
    
    return ProductSchema(
        id=product.id,
        name=product.name,
        sku=product.sku,
        primary_category=product.primary_category,
        product_type_id=product.product_type_id,
        base_unit_code=product.base_unit_code,
        is_composite=product.is_composite,
        is_active=product.is_active,
        tax_flags=product.tax_flags,
        unit_cost=product.unit_cost,
        attributes=attrs,
        components=comps
    )


@router.post("", response_model=ProductSchema)
def create_product(product_create: ProductCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    
    # Create the product
    db_product = Product(
        name=product_create.name,
        sku=product_create.sku,
        primary_category=product_create.primary_category,
        product_type_id=product_create.product_type_id,
        base_unit_code=product_create.base_unit_code,
        is_composite=product_create.is_composite,
        is_active=product_create.is_active,
        tax_flags=product_create.tax_flags,
        unit_cost=product_create.unit_cost
    )
    db.add(db_product)
    db.flush()

    # Add attributes
    for attr in product_create.attributes:
        # Get the attribute definition to know the data type
        attr_def = db.query(AttributeDefinition).filter(AttributeDefinition.id == attr.attribute_definition_id).first()
        if not attr_def:
            raise HTTPException(status_code=400, detail=f"Attribute definition {attr.attribute_definition_id} not found")

        # Validate the value type matches the definition
        if attr_def.data_type == "number" and not isinstance(attr.value, (int, float)):
            raise HTTPException(status_code=400, detail=f"Expected number for attribute {attr_def.name}")
        elif attr_def.data_type == "boolean" and not isinstance(attr.value, bool):
            raise HTTPException(status_code=400, detail=f"Expected boolean for attribute {attr_def.name}")
        elif attr_def.data_type == "string" and not isinstance(attr.value, str):
            raise HTTPException(status_code=400, detail=f"Expected string for attribute {attr_def.name}")

        db_attr = ProductAttributeValue(
            product_id=db_product.id,
            attribute_definition_id=attr.attribute_definition_id,
            value_number=attr.value if attr_def.data_type == "number" else None,
            value_boolean=attr.value if attr_def.data_type == "boolean" else None,
            value_string=str(attr.value) if attr_def.data_type == "string" else None
        )
        db.add(db_attr)

    # Add components (only for composite products)
    if product_create.is_composite:
        for comp in product_create.components:
            component_product_id = comp.get('component_product_id')
            quantity = comp.get('quantity', 1.0)
            unit_code = comp.get('unit_code', db_product.base_unit_code)
            substitution_allowed = comp.get('substitution_allowed', False)
            
            db_comp = CompositeComponent(
                parent_product_id=db_product.id,
                component_product_id=component_product_id,
                quantity=quantity,
                unit_code=unit_code,
                substitution_allowed=substitution_allowed
            )
            db.add(db_comp)

    db.commit()
    db.refresh(db_product)
    
    # Get the created product with all relationships loaded
    product_with_rels = db.query(Product).options(
        joinedload(Product.product_type),
        joinedload(Product.attributes).joinedload(ProductAttributeValue.attribute_definition),
        joinedload(Product.components).joinedload(CompositeComponent.component_product)
    ).filter(Product.id == db_product.id).first()
    
    # Get attributes
    attrs = {}
    for av in product_with_rels.attributes:
        defn = av.attribute_definition
        if defn.data_type == "number":
            val = av.value_number
        elif defn.data_type == "boolean":
            val = av.value_boolean
        else:
            val = av.value_string
        attrs[defn.code] = val
    
    # Get components
    comps = [{
        "component_product_id": c.component_product_id, 
        "quantity": float(c.quantity),
        "unit_code": c.unit_code,
        "substitution_allowed": c.substitution_allowed
    } for c in product_with_rels.components]
    
    return ProductSchema(
        id=product_with_rels.id,
        name=product_with_rels.name,
        sku=product_with_rels.sku,
        primary_category=product_with_rels.primary_category,
        product_type_id=product_with_rels.product_type_id,
        base_unit_code=product_with_rels.base_unit_code,
        is_composite=product_with_rels.is_composite,
        is_active=product_with_rels.is_active,
        tax_flags=product_with_rels.tax_flags,
        unit_cost=product_with_rels.unit_cost,
        attributes=attrs,
        components=comps
    )


@router.put("/{product_id}", response_model=ProductSchema)
def update_product(product_id: int, product_update: ProductUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update basic fields
    if product_update.name is not None:
        product.name = product_update.name
    if product_update.sku is not None:
        product.sku = product_update.sku
    if product_update.primary_category is not None:
        product.primary_category = product_update.primary_category
    if product_update.product_type_id is not None:
        product.product_type_id = product_update.product_type_id
    if product_update.base_unit_code is not None:
        product.base_unit_code = product_update.base_unit_code
    if product_update.is_composite is not None:
        product.is_composite = product_update.is_composite
    if product_update.is_active is not None:
        product.is_active = product_update.is_active
    if product_update.tax_flags is not None:
        product.tax_flags = product_update.tax_flags
    if product_update.unit_cost is not None:
        product.unit_cost = product_update.unit_cost
    
    # Remove old attributes
    db.query(ProductAttributeValue).filter(ProductAttributeValue.product_id == product_id).delete()
    
    # Add new attributes
    for attr in product_update.attributes:
        # Get the attribute definition to know the data type
        attr_def = db.query(AttributeDefinition).filter(AttributeDefinition.id == attr.attribute_definition_id).first()
        if not attr_def:
            raise HTTPException(status_code=400, detail=f"Attribute definition {attr.attribute_definition_id} not found")

        # Validate the value type matches the definition
        if attr_def.data_type == "number" and not isinstance(attr.value, (int, float)):
            raise HTTPException(status_code=400, detail=f"Expected number for attribute {attr_def.name}")
        elif attr_def.data_type == "boolean" and not isinstance(attr.value, bool):
            raise HTTPException(status_code=400, detail=f"Expected boolean for attribute {attr_def.name}")
        elif attr_def.data_type == "string" and not isinstance(attr.value, str):
            raise HTTPException(status_code=400, detail=f"Expected string for attribute {attr_def.name}")

        db_attr = ProductAttributeValue(
            product_id=product.id,
            attribute_definition_id=attr.attribute_definition_id,
            value_number=attr.value if attr_def.data_type == "number" else None,
            value_boolean=attr.value if attr_def.data_type == "boolean" else None,
            value_string=str(attr.value) if attr_def.data_type == "string" else None
        )
        db.add(db_attr)

    # Remove old components
    db.query(CompositeComponent).filter(CompositeComponent.parent_product_id == product_id).delete()
    
    # Add new components (only for composite products)
    if product_update.is_composite:
        for comp in product_update.components:
            component_product_id = comp.get('component_product_id')
            quantity = comp.get('quantity', 1.0)
            unit_code = comp.get('unit_code', product.base_unit_code)
            substitution_allowed = comp.get('substitution_allowed', False)
            
            db_comp = CompositeComponent(
                parent_product_id=product.id,
                component_product_id=component_product_id,
                quantity=quantity,
                unit_code=unit_code,
                substitution_allowed=substitution_allowed
            )
            db.add(db_comp)

    db.commit()
    db.refresh(product)
    
    # Get the updated product with all relationships loaded
    product_with_rels = db.query(Product).options(
        joinedload(Product.product_type),
        joinedload(Product.attributes).joinedload(ProductAttributeValue.attribute_definition),
        joinedload(Product.components).joinedload(CompositeComponent.component_product)
    ).filter(Product.id == product.id).first()
    
    # Get attributes
    attrs = {}
    for av in product_with_rels.attributes:
        defn = av.attribute_definition
        if defn.data_type == "number":
            val = av.value_number
        elif defn.data_type == "boolean":
            val = av.value_boolean
        else:
            val = av.value_string
        attrs[defn.code] = val
    
    # Get components
    comps = [{
        "component_product_id": c.component_product_id, 
        "quantity": float(c.quantity),
        "unit_code": c.unit_code,
        "substitution_allowed": c.substitution_allowed
    } for c in product_with_rels.components]
    
    return ProductSchema(
        id=product_with_rels.id,
        name=product_with_rels.name,
        sku=product_with_rels.sku,
        primary_category=product_with_rels.primary_category,
        product_type_id=product_with_rels.product_type_id,
        base_unit_code=product_with_rels.base_unit_code,
        is_composite=product_with_rels.is_composite,
        is_active=product_with_rels.is_active,
        tax_flags=product_with_rels.tax_flags,
        unit_cost=product_with_rels.unit_cost,
        attributes=attrs,
        components=comps
    )


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}
