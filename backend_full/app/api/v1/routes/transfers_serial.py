from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.models.models import TransferDoc, TransferLine
from app.services.serial_transfers import TransferService


router = APIRouter(prefix="/transfers", tags=["serial-transfers"])


@router.post("", response_model=schemas.TransferDocOut)
def create_transfer(
    payload: schemas.TransferCreate,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    doc = service.create(payload.from_location_id, payload.to_location_id, created_by_user_id=getattr(user, "id", None))
    db.commit()
    return schemas.TransferDocOut.model_validate(doc)


@router.get("", response_model=list[schemas.TransferDocListOut])
def list_transfers(
    status: str | None = Query(default=None),
    from_location_id: int | None = Query(default=None),
    to_location_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    created_by_user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    query = db.query(TransferDoc)
    if product_id is not None:
        query = query.join(TransferLine, TransferLine.transfer_doc_id == TransferDoc.id).filter(TransferLine.product_id == product_id)
    if status:
        query = query.filter(TransferDoc.status == status)
    if from_location_id is not None:
        query = query.filter(TransferDoc.from_location_id == from_location_id)
    if to_location_id is not None:
        query = query.filter(TransferDoc.to_location_id == to_location_id)
    if created_by_user_id is not None:
        query = query.filter(TransferDoc.created_by_user_id == created_by_user_id)
    if product_id is not None:
        query = query.distinct()
    query = query.order_by(TransferDoc.id.desc()).offset(offset).limit(limit)
    return [schemas.TransferDocListOut.model_validate(row) for row in query.all()]


@router.post("/{transfer_doc_id}/plan", response_model=schemas.TransferPlanOut)
def plan_transfer(
    transfer_doc_id: int,
    payload: schemas.TransferPlan,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.plan_fifo(transfer_doc_id, payload.product_id, payload.qty_base)
    db.commit()
    return schemas.TransferPlanOut(
        transfer_doc_id=transfer_doc_id,
        transfer_line_id=result.transfer_line_id,
        planned_items=result.planned_items,
    )


@router.post("/{transfer_doc_id}/remove-item")
def remove_transfer_item(
    transfer_doc_id: int,
    payload: schemas.TransferRemoveItem,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.remove_planned_item(transfer_doc_id, payload.product_item_id)
    db.commit()
    return result


@router.post("/{transfer_doc_id}/scan")
def scan_transfer(
    transfer_doc_id: int,
    payload: schemas.TransferScan,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.scan(transfer_doc_id, payload.qr_code, payload.mode)
    db.commit()
    return result


@router.post("/{transfer_doc_id}/ship")
def ship_transfer(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.ship(transfer_doc_id)
    db.commit()
    return result


@router.post("/{transfer_doc_id}/close")
def close_transfer(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.close(transfer_doc_id)
    db.commit()
    return result
