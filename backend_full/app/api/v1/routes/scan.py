from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.services.serial_qr import parse_qr
from app.models.models import ProductItem, Box


router = APIRouter(prefix="/scan", tags=["serial-scan"])


@router.post("/{qr_code}", response_model=schemas.ScanOut)
def scan_qr(
    qr_code: str,
    user=Depends(PermissionChecker(["qr.scan"])),
    db: Session = Depends(get_db),
):
    parsed = parse_qr(qr_code)
    if parsed.kind == "ITM":
        item = db.query(ProductItem).filter(ProductItem.uuid == parsed.uuid).first()
        if not item:
            return schemas.ScanOut(kind="ITM", found=False, uuid=parsed.uuid)
        return schemas.ScanOut(
            kind="ITM",
            found=True,
            uuid=item.uuid,
            id=item.id,
            status=item.status,
            location_id=item.location_id,
            product_id=item.product_id,
            lot_id=item.lot_id,
            box_id=item.box_id,
            reserved_transfer_doc_id=item.reserved_transfer_doc_id,
        )
    box = db.query(Box).filter(Box.uuid == parsed.uuid).first()
    if not box:
        return schemas.ScanOut(kind="BOX", found=False, uuid=parsed.uuid)
    return schemas.ScanOut(
        kind="BOX",
        found=True,
        uuid=box.uuid,
        id=box.id,
        status=box.status,
        location_id=box.location_id,
        product_id=box.product_id,
        lot_id=box.lot_id,
        sealed=box.sealed,
    )
