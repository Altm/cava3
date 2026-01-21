from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db
from app.security.hmac import verify_hmac_signature
from app.models.models import Terminal
from app.services.sales_service import SalesService

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
