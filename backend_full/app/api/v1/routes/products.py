from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db, PermissionChecker, allow_public
from app.models.models import Product

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(user=Depends(PermissionChecker(["product.read"])), db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return jsonable_encoder(products)


@router.post("")
def create_product(payload: dict, user=Depends(PermissionChecker(["product.write"])), db: Session = Depends(get_db)):
    product = Product(**payload)
    db.add(product)
    db.commit()
    db.refresh(product)
    return jsonable_encoder(product)


@router.put("/{product_id}")
def update_product(product_id: int, payload: dict, user=Depends(PermissionChecker(["product.write"])), db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in payload.items():
        setattr(product, k, v)
    db.commit()
    db.refresh(product)
    return jsonable_encoder(product)
