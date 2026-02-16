from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.models.models import Receipt, ReceiptLine
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


@router.get("", response_model=list[schemas.ReceiptListOut])
def list_receipts(
    status: str | None = Query(default=None),
    to_location_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    created_by_user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["receipts.read"])),
    db: Session = Depends(get_db),
):
    query = db.query(Receipt)
    if product_id is not None:
        query = query.join(ReceiptLine, ReceiptLine.receipt_id == Receipt.id).filter(ReceiptLine.product_id == product_id)
    if status:
        query = query.filter(Receipt.status == status)
    if to_location_id is not None:
        query = query.filter(Receipt.to_location_id == to_location_id)
    if created_by_user_id is not None:
        query = query.filter(Receipt.created_by_user_id == created_by_user_id)
    if product_id is not None:
        query = query.distinct()
    query = query.order_by(Receipt.id.desc()).offset(offset).limit(limit)
    return [schemas.ReceiptListOut.model_validate(row) for row in query.all()]


@router.get("/{receipt_id}", response_model=schemas.ReceiptListOut)
def get_receipt(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.read"])),
    db: Session = Depends(get_db),
):
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return schemas.ReceiptListOut.model_validate(receipt)


@router.get("/{receipt_id}/lines", response_model=list[schemas.ReceiptLineOut])
def get_receipt_lines(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.read"])),
    db: Session = Depends(get_db),
):
    exists = db.query(Receipt.id).filter(Receipt.id == receipt_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Receipt not found")
    rows = (
        db.query(ReceiptLine)
        .filter(ReceiptLine.receipt_id == receipt_id)
        .order_by(ReceiptLine.id.asc())
        .all()
    )
    return [schemas.ReceiptLineOut.model_validate(row) for row in rows]


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


@router.post("/{receipt_id}/lines/{line_id}/remove")
def remove_receipt_line(
    receipt_id: int,
    line_id: int,
    user=Depends(PermissionChecker(["receipts.write"])),
    db: Session = Depends(get_db),
):
    service = ReceiptService(db)
    result = service.remove_line(receipt_id=receipt_id, line_id=line_id)
    db.commit()
    return result


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


@router.post("/{receipt_id}/auto-box", response_model=schemas.ReceiptAutoBoxOut)
def receipt_auto_box(
    receipt_id: int,
    payload: schemas.ReceiptAutoBoxRequest,
    user=Depends(PermissionChecker(["receipts.write"])),
    db: Session = Depends(get_db),
):
    service = ReceiptService(db)
    result = service.auto_box(
        receipt_id=receipt_id,
        items_per_box=payload.items_per_box,
        max_boxes=payload.max_boxes,
        include_partial=payload.include_partial,
        seal_full_boxes=payload.seal_full_boxes,
        product_id=payload.product_id,
        lot_id=payload.lot_id,
    )
    db.commit()
    return schemas.ReceiptAutoBoxOut(
        receipt_id=result.receipt_id,
        items_per_box=result.items_per_box,
        boxes_created=result.boxes_created,
        items_packed=result.items_packed,
        items_remaining_unboxed=result.items_remaining_unboxed,
        boxes=[
            schemas.ReceiptAutoBoxBoxOut(
                id=box.id,
                qr_code=box.qr_code,
                product_id=box.product_id,
                lot_id=box.lot_id,
                location_id=box.location_id,
                sealed=box.sealed,
                packed_items=box.packed_items,
            )
            for box in result.boxes
        ],
    )
