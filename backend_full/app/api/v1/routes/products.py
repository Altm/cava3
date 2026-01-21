from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db, get_current_user, check_permission
from app.models.models import Product

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.read", db=db)
    products = db.query(Product).all()
    return jsonable_encoder(products)


@router.post("")
def create_product(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    product = Product(**payload)
    db.add(product)
    db.commit()
    db.refresh(product)
    return jsonable_encoder(product)


@router.put("/{product_id}")
def update_product(product_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "product.write", db=db)
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in payload.items():
        setattr(product, k, v)
    db.commit()
    db.refresh(product)
    return jsonable_encoder(product)
