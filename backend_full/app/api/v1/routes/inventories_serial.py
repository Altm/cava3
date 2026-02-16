from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
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

