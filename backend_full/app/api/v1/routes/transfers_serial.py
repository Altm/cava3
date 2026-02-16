from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_db, PermissionChecker
from app.schemas import serial as schemas
from app.models.models import TransferDoc, TransferLine, TransferItem, Product, ProductItem
from app.services.serial_transfers import TransferService


router = APIRouter(prefix="/transfers", tags=["serial-transfers"])


@router.post("", response_model=schemas.TransferDocOut)
def create_transfer(
    payload: schemas.TransferCreate,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    doc = service.create(payload.from_location_id, payload.to_location_id, created_by_user_id=getattr(user, "id", None))
    db.commit()
    return schemas.TransferDocOut.model_validate(doc)


@router.get("", response_model=list[schemas.TransferDocListOut])
def list_transfers(
    status: str | None = Query(default=None),
    from_location_id: int | None = Query(default=None),
    to_location_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    created_by_user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    query = db.query(TransferDoc)
    if product_id is not None:
        query = query.join(TransferLine, TransferLine.transfer_doc_id == TransferDoc.id).filter(TransferLine.product_id == product_id)
    if status:
        query = query.filter(TransferDoc.status == status)
    if from_location_id is not None:
        query = query.filter(TransferDoc.from_location_id == from_location_id)
    if to_location_id is not None:
        query = query.filter(TransferDoc.to_location_id == to_location_id)
    if created_by_user_id is not None:
        query = query.filter(TransferDoc.created_by_user_id == created_by_user_id)
    if product_id is not None:
        query = query.distinct()
    query = query.order_by(TransferDoc.id.desc()).offset(offset).limit(limit)
    return [schemas.TransferDocListOut.model_validate(row) for row in query.all()]


@router.get("/{transfer_doc_id}", response_model=schemas.TransferDocDetailOut)
def get_transfer(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    doc = db.query(TransferDoc).filter(TransferDoc.id == transfer_doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Transfer not found")

    base_query = (
        db.query(TransferItem)
        .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
        .filter(TransferLine.transfer_doc_id == transfer_doc_id)
    )
    planned_count = base_query.filter(TransferItem.state == "planned").count()
    picked_count = base_query.filter(TransferItem.state == "picked").count()
    removed_count = base_query.filter(TransferItem.state == "removed").count()
    received_count = (
        db.query(func.count(TransferItem.id))
        .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
        .filter(TransferLine.transfer_doc_id == transfer_doc_id, TransferItem.received_at.isnot(None))
        .scalar()
        or 0
    )
    line_rows = (
        db.query(
            TransferLine.id.label("transfer_line_id"),
            TransferLine.product_id,
            TransferLine.qty_base,
            TransferLine.pick_policy,
            Product.name.label("product_name"),
        )
        .join(Product, Product.id == TransferLine.product_id)
        .filter(TransferLine.transfer_doc_id == transfer_doc_id)
        .order_by(TransferLine.id.asc())
        .all()
    )
    qr_rows = (
        db.query(
            TransferItem.transfer_line_id,
            ProductItem.qr_code,
        )
        .join(ProductItem, ProductItem.id == TransferItem.product_item_id)
        .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
        .filter(TransferLine.transfer_doc_id == transfer_doc_id, TransferItem.state == "planned")
        .order_by(TransferItem.transfer_line_id.asc(), TransferItem.id.asc())
        .all()
    )
    planned_qr_codes_by_line: dict[int, list[str]] = {}
    for transfer_line_id, qr_code in qr_rows:
        planned_qr_codes_by_line.setdefault(transfer_line_id, []).append(qr_code)
    transfer_lines = [
        schemas.TransferPlanLineOut(
            transfer_line_id=row.transfer_line_id,
            product_id=row.product_id,
            product_name=row.product_name,
            qty_base=row.qty_base,
            pick_policy=row.pick_policy,
            planned_qr_codes=planned_qr_codes_by_line.get(row.transfer_line_id, []),
        )
        for row in line_rows
    ]

    return schemas.TransferDocDetailOut(
        id=doc.id,
        from_location_id=doc.from_location_id,
        to_location_id=doc.to_location_id,
        status=doc.status,
        created_by_user_id=doc.created_by_user_id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        planned_count=planned_count,
        picked_count=picked_count,
        received_count=int(received_count),
        removed_count=removed_count,
        transfer_lines=transfer_lines,
    )


@router.get("/{transfer_doc_id}/items", response_model=list[schemas.TransferItemMovementOut])
def list_transfer_items(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    doc = db.query(TransferDoc).filter(TransferDoc.id == transfer_doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Transfer not found")

    rows = (
        db.query(
            TransferItem.id.label("transfer_item_id"),
            TransferItem.product_item_id,
            TransferItem.state.label("transfer_item_state"),
            TransferItem.picked_at.label("shipped_at"),
            TransferItem.received_at,
            ProductItem.qr_code.label("product_item_qr_code"),
            ProductItem.status.label("product_item_status"),
            ProductItem.lost_reason,
            ProductItem.lost_doc_type,
            ProductItem.lost_doc_id,
            TransferLine.product_id,
            Product.name.label("product_name"),
        )
        .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
        .join(ProductItem, ProductItem.id == TransferItem.product_item_id)
        .join(Product, Product.id == TransferLine.product_id)
        .filter(TransferLine.transfer_doc_id == transfer_doc_id)
        .order_by(TransferItem.id.asc())
        .all()
    )

    result: list[schemas.TransferItemMovementOut] = []
    for row in rows:
        is_closed_not_received = doc.status == "closed" and row.transfer_item_state == "picked" and row.received_at is None
        is_lost_item = (
            row.product_item_status == "lost"
            and row.lost_reason == "lost_in_transit"
            and row.lost_doc_type == "transfer"
            and row.lost_doc_id == doc.id
        )
        result.append(
            schemas.TransferItemMovementOut(
                transfer_item_id=row.transfer_item_id,
                product_item_id=row.product_item_id,
                product_item_qr_code=row.product_item_qr_code,
                product_id=row.product_id,
                product_name=row.product_name,
                transfer_item_state=row.transfer_item_state,
                transfer_status=doc.status,
                transfer_created_at=doc.created_at,
                shipped_at=row.shipped_at,
                received_at=row.received_at,
                is_lost=bool(is_closed_not_received or is_lost_item),
            )
        )
    return result


@router.post("/{transfer_doc_id}/plan", response_model=schemas.TransferPlanOut)
def plan_transfer(
    transfer_doc_id: int,
    payload: schemas.TransferPlan,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.plan_fifo(transfer_doc_id, payload.product_id, payload.qty_base)
    db.commit()
    return schemas.TransferPlanOut(
        transfer_doc_id=transfer_doc_id,
        transfer_line_id=result.transfer_line_id,
        planned_items=result.planned_items,
    )


@router.post("/{transfer_doc_id}/remove-item")
def remove_transfer_item(
    transfer_doc_id: int,
    payload: schemas.TransferRemoveItem,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.remove_planned_item(transfer_doc_id, payload.product_item_id)
    db.commit()
    return result


@router.post("/{transfer_doc_id}/scan")
def scan_transfer(
    transfer_doc_id: int,
    payload: schemas.TransferScan,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.scan(transfer_doc_id, payload.qr_code, payload.mode)
    db.commit()
    return result


@router.post("/{transfer_doc_id}/ship")
def ship_transfer(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.ship(transfer_doc_id)
    db.commit()
    return result


@router.post("/{transfer_doc_id}/close")
def close_transfer(
    transfer_doc_id: int,
    user=Depends(PermissionChecker(["transfers.write"])),
    db: Session = Depends(get_db),
):
    service = TransferService(db)
    result = service.close(transfer_doc_id)
    db.commit()
    return result
