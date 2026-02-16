from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.models.models import InventoryDoc
from app.services.serial_inventories import InventoryService


router = APIRouter(prefix="/inventories", tags=["serial-inventories"])


@router.post("", response_model=schemas.InventoryDocOut)
def create_inventory(
    payload: schemas.InventoryCreate,
    user=Depends(PermissionChecker(["inventories.write"])),
    db: Session = Depends(get_db),
):
    service = InventoryService(db)
    doc = service.create(payload.location_id, created_by_user_id=getattr(user, "id", None))
    db.commit()
    return schemas.InventoryDocOut.model_validate(doc)


@router.get("", response_model=list[schemas.InventoryDocListOut])
def list_inventories(
    status: str | None = Query(default=None),
    location_id: int | None = Query(default=None),
    created_by_user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["inventories.write"])),
    db: Session = Depends(get_db),
):
    query = db.query(InventoryDoc)
    if status:
        query = query.filter(InventoryDoc.status == status)
    if location_id is not None:
        query = query.filter(InventoryDoc.location_id == location_id)
    if created_by_user_id is not None:
        query = query.filter(InventoryDoc.created_by_user_id == created_by_user_id)
    query = query.order_by(InventoryDoc.id.desc()).offset(offset).limit(limit)
    return [schemas.InventoryDocListOut.model_validate(row) for row in query.all()]


@router.post("/{inventory_doc_id}/start")
def start_inventory(
    inventory_doc_id: int,
    user=Depends(PermissionChecker(["inventories.write"])),
    db: Session = Depends(get_db),
):
    service = InventoryService(db)
    result = service.start(inventory_doc_id)
    db.commit()
    return result


@router.post("/{inventory_doc_id}/scan")
def scan_inventory(
    inventory_doc_id: int,
    payload: schemas.InventoryScan,
    user=Depends(PermissionChecker(["inventories.write"])),
    db: Session = Depends(get_db),
):
    service = InventoryService(db)
    result = service.scan(inventory_doc_id, payload.qr_code)
    db.commit()
    return result


@router.post("/{inventory_doc_id}/close")
def close_inventory(
    inventory_doc_id: int,
    user=Depends(PermissionChecker(["inventories.write"])),
    db: Session = Depends(get_db),
):
    service = InventoryService(db)
    result = service.close(inventory_doc_id)
    db.commit()
    return result
