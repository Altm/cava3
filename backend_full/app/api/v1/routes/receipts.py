from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.models.models import Receipt, ReceiptLine, ProductItem, StockLot, Product, Box, Location
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


@router.get("/{receipt_id}/items", response_model=list[schemas.ReceiptItemContentOut])
def get_receipt_items(
    receipt_id: int,
    user=Depends(PermissionChecker(["receipts.read"])),
    db: Session = Depends(get_db),
):
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    rows = (
        db.query(
            ProductItem.id.label("product_item_id"),
            ProductItem.qr_code.label("product_item_qr_code"),
            ProductItem.status.label("product_item_status"),
            ProductItem.created_at.label("product_item_created_at"),
            ProductItem.updated_at.label("product_item_updated_at"),
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
            Product.base_cost.label("purchase_amount"),
            StockLot.id.label("lot_id"),
            StockLot.supplier_lot_number,
            StockLot.received_at.label("lot_received_at"),
            Box.id.label("box_id"),
            Box.qr_code.label("box_qr_code"),
            Location.id.label("location_id"),
            Location.name.label("location_name"),
            Location.code.label("location_code"),
        )
        .join(StockLot, StockLot.id == ProductItem.lot_id)
        .join(Product, Product.id == ProductItem.product_id)
        .join(Location, Location.id == ProductItem.location_id)
        .outerjoin(Box, Box.id == ProductItem.box_id)
        .filter(StockLot.receipt_id == receipt_id)
        .order_by(ProductItem.id.asc())
        .all()
    )
    return [
        schemas.ReceiptItemContentOut(
            product_item_id=row.product_item_id,
            product_item_qr_code=row.product_item_qr_code,
            product_item_status=row.product_item_status,
            product_item_created_at=row.product_item_created_at,
            product_item_updated_at=row.product_item_updated_at,
            product_id=row.product_id,
            product_name=row.product_name,
            product_sku=row.product_sku,
            purchase_amount=Decimal(str(row.purchase_amount)) if row.purchase_amount is not None else Decimal("0"),
            lot_id=row.lot_id,
            supplier_lot_number=row.supplier_lot_number,
            lot_received_at=row.lot_received_at,
            box_id=row.box_id,
            box_qr_code=row.box_qr_code,
            location_id=row.location_id,
            location_name=row.location_name,
            location_code=row.location_code,
            receipt_id=receipt.id,
            receipt_status=receipt.status,
            receipt_created_at=receipt.created_at,
        )
        for row in rows
    ]


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
