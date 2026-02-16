from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.models.models import Box
from app.services.serial_boxes import BoxService


router = APIRouter(prefix="/boxes", tags=["serial-boxes"])


@router.post("", response_model=schemas.BoxOut)
def create_box(
    payload: schemas.BoxCreate,
    user=Depends(PermissionChecker(["boxes.write"])),
    db: Session = Depends(get_db),
):
    service = BoxService(db)
    box = service.create(
        product_id=payload.product_id,
        lot_id=payload.lot_id,
        location_id=payload.location_id,
        sealed=payload.sealed,
    )
    db.commit()
    return schemas.BoxOut.model_validate(box)


@router.get("", response_model=list[schemas.BoxListOut])
def list_boxes(
    status: str | None = Query(default=None),
    sealed: bool | None = Query(default=None),
    location_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    lot_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["boxes.read"])),
    db: Session = Depends(get_db),
):
    query = db.query(Box)
    if status:
        query = query.filter(Box.status == status)
    if sealed is not None:
        query = query.filter(Box.sealed == sealed)
    if location_id is not None:
        query = query.filter(Box.location_id == location_id)
    if product_id is not None:
        query = query.filter(Box.product_id == product_id)
    if lot_id is not None:
        query = query.filter(Box.lot_id == lot_id)
    query = query.order_by(Box.id.desc()).offset(offset).limit(limit)
    return [schemas.BoxListOut.model_validate(row) for row in query.all()]


@router.get("/{box_id}", response_model=schemas.BoxOut)
def get_box(
    box_id: int,
    user=Depends(PermissionChecker(["boxes.read"])),
    db: Session = Depends(get_db),
):
    box = db.query(Box).filter(Box.id == box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail="Box not found")
    return schemas.BoxOut.model_validate(box)


@router.post("/{box_id}/open", response_model=schemas.BoxOut)
def open_box(
    box_id: int,
    user=Depends(PermissionChecker(["boxes.write"])),
    db: Session = Depends(get_db),
):
    service = BoxService(db)
    box = service.open_box(box_id)
    db.commit()
    return schemas.BoxOut.model_validate(box)


@router.post("/{box_id}/seal", response_model=schemas.BoxOut)
def seal_box(
    box_id: int,
    user=Depends(PermissionChecker(["boxes.write"])),
    db: Session = Depends(get_db),
):
    service = BoxService(db)
    box = service.seal_box(box_id)
    db.commit()
    return schemas.BoxOut.model_validate(box)


@router.post("/{box_id}/add-item")
def add_item_to_box(
    box_id: int,
    payload: schemas.BoxAddItem,
    user=Depends(PermissionChecker(["boxes.write"])),
    db: Session = Depends(get_db),
):
    service = BoxService(db)
    result = service.add_item_by_qr(box_id, payload.qr_code)
    db.commit()
    return result


@router.get("/{box_id}/labels", response_model=schemas.LabelsOut)
def box_labels(
    box_id: int,
    user=Depends(PermissionChecker(["boxes.read"])),
    db: Session = Depends(get_db),
):
    service = BoxService(db)
    return schemas.LabelsOut(labels=service.list_box_labels(box_id))
