from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
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

