from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.services.serial_qr import parse_qr
from app.models.models import ProductItem, Box


router = APIRouter(prefix="/scan", tags=["serial-scan"])


@router.get("/items", response_model=list[schemas.ProductItemListOut])
def list_product_items(
    status: str | None = Query(default=None),
    location_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    lot_id: int | None = Query(default=None),
    box_id: int | None = Query(default=None),
    reserved_transfer_doc_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["qr.scan"])),
    db: Session = Depends(get_db),
):
    query = db.query(ProductItem)
    if status:
        query = query.filter(ProductItem.status == status)
    if location_id is not None:
        query = query.filter(ProductItem.location_id == location_id)
    if product_id is not None:
        query = query.filter(ProductItem.product_id == product_id)
    if lot_id is not None:
        query = query.filter(ProductItem.lot_id == lot_id)
    if box_id is not None:
        query = query.filter(ProductItem.box_id == box_id)
    if reserved_transfer_doc_id is not None:
        query = query.filter(ProductItem.reserved_transfer_doc_id == reserved_transfer_doc_id)
    query = query.order_by(ProductItem.id.desc()).offset(offset).limit(limit)
    return [schemas.ProductItemListOut.model_validate(row) for row in query.all()]


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
