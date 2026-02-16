from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
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
