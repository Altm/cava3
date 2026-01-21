from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db, get_current_user, check_permission
from app.services.stock_service import StockService

router = APIRouter(prefix="/stock", tags=["stock"])


@router.post("/adjust")
def adjust_stock(payload: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    check_permission(user, "stock.write", location_id=payload["location_id"], db=db)
    service = StockService(db)
    stock = service.adjust_stock(
        location_id=payload["location_id"],
        product_id=payload["product_id"],
        quantity=Decimal(str(payload["quantity"])),
        unit_code=payload["unit"],
    )
    db.commit()
    return {"product_id": stock.product_id, "location_id": stock.location_id, "quantity": float(stock.quantity)}
