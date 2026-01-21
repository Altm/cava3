from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db, get_current_user, check_permission
from app.security.hmac import verify_hmac_signature
from app.models.models import Terminal, Product, CompositeComponent, Stock
from app.services.sales_service import SalesService
from app.schemas.product_schemas import SaleRequest
from decimal import Decimal

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("")
async def submit_sale(
    request: Request,
    payload: dict,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    db: Session = Depends(get_db),
):
    verify_hmac_signature(request.method, request.url.path, await request.body(), x_terminal_id, x_signature, x_timestamp)
    terminal = db.query(Terminal).filter_by(terminal_id=x_terminal_id).first()
    if not terminal:
        raise HTTPException(status_code=401, detail="Unknown terminal")
    service = SalesService(db)
    sale = service.ingest_sale(payload["event_id"], terminal.id, terminal.location_id, payload["lines"])
    db.commit()
    return {"event_id": sale.event_id, "status": sale.status}


@router.post("/daily-log")
async def daily_log(
    request: Request,
    payload: dict,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    db: Session = Depends(get_db),
):
    verify_hmac_signature(request.method, request.url.path, await request.body(), x_terminal_id, x_signature, x_timestamp)
    terminal = db.query(Terminal).filter_by(terminal_id=x_terminal_id).first()
    if not terminal:
        raise HTTPException(status_code=401, detail="Unknown terminal")
    service = SalesService(db)
    result = service.reconcile_daily(terminal.id, terminal.location_id, payload["events"])
    db.commit()
    return result


@router.post("/product-sale")
def sell_product(sale_request: SaleRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Endpoint to sell a product and reduce stock accordingly.
    For composite products, it will reduce the stock of all components.
    """
    check_permission(user, "product.write", db=db)
    
    product = db.query(Product).filter(Product.id == sale_request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Find stock item for this product at a default location (or use first location found)
    stock_item = db.query(Stock).filter(Stock.product_id == sale_request.product_id).first()
    if not stock_item:
        raise HTTPException(status_code=400, detail="No stock found for this product")
    
    if stock_item.quantity < Decimal(str(sale_request.quantity)):
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    # Calculate total cost for the sold items
    unit_cost = product.unit_cost or 0.0
    total_cost = unit_cost * sale_request.quantity
    
    if product.is_composite:
        # For composite products, reduce the stock of all components
        components = db.query(CompositeComponent).filter(
            CompositeComponent.parent_product_id == product.id
        ).all()
        
        for comp in components:
            component_product = db.query(Product).filter(Product.id == comp.component_product_id).first()
            if not component_product:
                raise HTTPException(status_code=404, detail=f"Component product {comp.component_product_id} not found")
            
            # Find stock item for component
            component_stock = db.query(Stock).filter(
                Stock.product_id == comp.component_product_id
            ).first()
            
            if not component_stock:
                raise HTTPException(status_code=404, detail=f"No stock found for component {comp.component_product_id}")
            
            # Calculate the amount of component needed for the sale
            required_amount = float(comp.quantity) * sale_request.quantity
            
            if component_stock.quantity < Decimal(str(required_amount)):
                raise HTTPException(status_code=400, detail=f"Insufficient stock for component {component_product.name}")
            
            # Reduce the component's stock
            component_stock.quantity -= Decimal(str(required_amount))
        
        # Reduce the composite product's stock
        stock_item.quantity -= Decimal(str(sale_request.quantity))
    else:
        # For simple products, just reduce the stock
        stock_item.quantity -= Decimal(str(sale_request.quantity))
    
    db.commit()
    
    return {
        "message": f"Successfully sold {sale_request.quantity} of {product.name}",
        "total_cost": total_cost
    }


@router.post("/glass-sale")
def sell_wine_glass(sale_request: SaleRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Endpoint to sell a glass of wine and reduce stock accordingly.
    It calculates how much of a bottle is consumed based on glasses per bottle attribute.
    """
    check_permission(user, "product.write", db=db)
    
    product = db.query(Product).filter(Product.id == sale_request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Find stock item for this product
    stock_item = db.query(Stock).filter(Stock.product_id == sale_request.product_id).first()
    if not stock_item:
        raise HTTPException(status_code=400, detail="No stock found for this product")
    
    # Since we don't have the attribute system fully implemented here, 
    # we'll simulate looking for a "glasses_per_bottle" attribute value
    # In a real implementation, we'd query the ProductAttributeValue table
    # For now, we'll assume the attribute exists as a property of the product
    # or use a default value
    
    # We need to find the glasses_per_bottle attribute value for this product
    # This would normally come from ProductAttributeValue table
    # For this implementation, we'll need to query the attribute values
    from app.models.models import ProductAttributeValue, AttributeDefinition
    
    # Find the attribute definition for "glasses_per_bottle"
    glasses_attr_def = db.query(AttributeDefinition).filter(
        AttributeDefinition.code == "glasses_per_bottle"
    ).first()
    
    if glasses_attr_def:
        # Find the value for this specific product
        glasses_attr_value = db.query(ProductAttributeValue).filter(
            ProductAttributeValue.product_id == sale_request.product_id,
            ProductAttributeValue.attribute_definition_id == glasses_attr_def.id
        ).first()
        
        if glasses_attr_value and glasses_attr_value.value_number:
            glasses_per_bottle = glasses_attr_value.value_number
        else:
            raise HTTPException(status_code=400, detail="This product does not support glass sales (missing glasses_per_bottle attribute)")
    else:
        raise HTTPException(status_code=400, detail="This product does not support glass sales (missing glasses_per_bottle attribute)")
    
    # Calculate how much of a bottle is being sold
    bottles_sold = sale_request.quantity / glasses_per_bottle
    
    if stock_item.quantity < Decimal(str(bottles_sold)):
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    # Calculate total cost for the sold items
    unit_cost = product.unit_cost or 0.0
    total_cost = unit_cost * bottles_sold
    
    # Reduce the stock
    stock_item.quantity -= Decimal(str(bottles_sold))
    
    db.commit()
    
    return {
        "message": f"Successfully sold {sale_request.quantity} glasses of {product.name}",
        "total_cost": total_cost
    }
