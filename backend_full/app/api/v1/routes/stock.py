from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db, require_permission
from app.services.stock_service import StockService

router = APIRouter(prefix="/stock", tags=["stock"])


@router.post("/adjust")
def adjust_stock(payload: dict, user=Depends(require_permission("stock.write")), db: Session = Depends(get_db)):
    service = StockService(db)
    stock = service.adjust_stock(
        location_id=payload["location_id"],
        product_id=payload["product_id"],
        quantity=Decimal(str(payload["quantity"])),
        unit_code=payload["unit"],
    )
    db.commit()
    return {"product_id": stock.product_id, "location_id": stock.location_id, "quantity": float(stock.quantity)}
