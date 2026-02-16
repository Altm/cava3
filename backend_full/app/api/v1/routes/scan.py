from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.services.serial_qr import parse_qr
from app.models.models import ProductItem, Box, Product, Stock, Location, TransferItem, TransferLine, TransferDoc


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


@router.get("/items/{product_item_id}/history", response_model=schemas.ProductItemHistoryOut)
def get_product_item_history(
    product_item_id: int,
    user=Depends(PermissionChecker(["qr.scan"])),
    db: Session = Depends(get_db),
):
    item = db.query(ProductItem).filter(ProductItem.id == product_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Product item not found")

    product = db.query(Product).filter(Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    current_base_cost = Decimal(str(product.base_cost)) if product.base_cost is not None else Decimal("0")
    summary = schemas.ProductItemHistorySummaryOut(
        product_item_id=item.id,
        product_item_qr_code=item.qr_code,
        product_item_status=item.status,
        product_item_location_id=item.location_id,
        product_id=product.id,
        product_name=product.name,
        product_sku=product.sku,
        lot_id=item.lot_id,
        current_base_cost=current_base_cost,
        item_purchase_amount=current_base_cost,
    )

    stock_rows = (
        db.query(Stock.location_id, Location.name, Stock.quantity)
        .join(Location, Location.id == Stock.location_id)
        .filter(Stock.product_id == item.product_id)
        .order_by(Stock.location_id.asc())
        .all()
    )
    stock_balances = [
        schemas.ProductStockBalanceOut(
            location_id=location_id,
            location_name=location_name,
            quantity=quantity,
        )
        for location_id, location_name, quantity in stock_rows
    ]

    transfer_rows = (
        db.query(
            TransferDoc.id.label("transfer_doc_id"),
            TransferDoc.from_location_id,
            TransferDoc.to_location_id,
            TransferDoc.status.label("transfer_status"),
            TransferDoc.created_at.label("transfer_created_at"),
            TransferItem.state.label("transfer_item_state"),
            TransferItem.picked_at.label("shipped_at"),
            TransferItem.received_at,
        )
        .join(TransferLine, TransferLine.transfer_doc_id == TransferDoc.id)
        .join(TransferItem, TransferItem.transfer_line_id == TransferLine.id)
        .filter(TransferItem.product_item_id == product_item_id)
        .order_by(TransferDoc.id.asc(), TransferItem.id.asc())
        .all()
    )
    transfers: list[schemas.ProductItemTransferHistoryOut] = []
    for row in transfer_rows:
        is_lost = bool(
            item.status == "lost"
            and item.lost_reason == "lost_in_transit"
            and item.lost_doc_type == "transfer"
            and item.lost_doc_id == row.transfer_doc_id
        ) or bool(row.transfer_status == "closed" and row.transfer_item_state == "picked" and row.received_at is None)
        transfers.append(
            schemas.ProductItemTransferHistoryOut(
                transfer_doc_id=row.transfer_doc_id,
                from_location_id=row.from_location_id,
                to_location_id=row.to_location_id,
                transfer_status=row.transfer_status,
                transfer_item_state=row.transfer_item_state,
                transfer_created_at=row.transfer_created_at,
                shipped_at=row.shipped_at,
                received_at=row.received_at,
                is_lost=is_lost,
            )
        )

    return schemas.ProductItemHistoryOut(summary=summary, stock_balances=stock_balances, transfers=transfers)


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
