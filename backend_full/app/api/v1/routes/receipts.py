from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.services.serial_receipts import ReceiptService


router = APIRouter(prefix="/receipts", tags=["serial-receipts"])


@router.post("", response_model=schemas.ReceiptOut)
def create_receipt(
    payload: schemas.ReceiptCreate,
    user=Depends(PermissionChecker(["receipts.write"])),
    db: Session = Depends(get_db),
):
    service = ReceiptService(db)
    receipt = service.create(to_location_id=payload.to_location_id, created_by_user_id=getattr(user, "id", None))
    db.commit()
    return schemas.ReceiptOut.model_validate(receipt)


@router.post("/{receipt_id}/lines", response_model=schemas.ReceiptLineOut)
def add_receipt_line(
    receipt_id: int,
    payload: schemas.ReceiptLineCreate,
    user=Depends(PermissionChecker(["receipts.write"])),
    db: Session = Depends(get_db),
):
    service = ReceiptService(db)
    line = service.add_line(
        receipt_id=receipt_id,
        product_id=payload.product_id,
        qty=Decimal(str(payload.qty)),
        unit_id=payload.unit_id,
        supplier_lot_number=payload.supplier_lot_number,
    )
    db.commit()
    return schemas.ReceiptLineOut.model_validate(line)


@router.post("/{receipt_id}/generate", response_model=schemas.ReceiptGenerateOut)
def generate_receipt(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.write"])),
    db: Session = Depends(get_db),
):
    service = ReceiptService(db)
    result = service.generate(receipt_id)
    db.commit()
    return schemas.ReceiptGenerateOut(receipt_id=receipt_id, lots_created=result.lots_created, items_created=result.items_created)


@router.post("/{receipt_id}/post")
def post_receipt(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.write"])),
    db: Session = Depends(get_db),
):
    service = ReceiptService(db)
    result = service.post(receipt_id)
    db.commit()
    return result


@router.post("/{receipt_id}/void")
def void_receipt(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.write"])),
    db: Session = Depends(get_db),
):
    service = ReceiptService(db)
    result = service.void(receipt_id)
    db.commit()
    return result


@router.get("/{receipt_id}/labels/items", response_model=schemas.LabelsOut)
def receipt_item_labels(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.read"])),
    db: Session = Depends(get_db),
):
    service = ReceiptService(db)
    labels = service.list_item_labels(receipt_id)
    return schemas.LabelsOut(labels=labels)

