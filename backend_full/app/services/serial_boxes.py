from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Box, ProductItem, StockLot
from app.services.serial_qr import parse_qr


class BoxService:
    """Create and manage boxes (1 product, 1 lot)."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, product_id: int, lot_id: int, location_id: int, sealed: bool = True) -> Box:
        lot = self.db.query(StockLot).get(lot_id)
        if not lot:
            raise HTTPException(status_code=404, detail="Lot not found")
        if lot.product_id != product_id:
            raise HTTPException(status_code=422, detail="Lot does not match product")
        box = Box(product_id=product_id, lot_id=lot_id, location_id=location_id, sealed=sealed, status="active")
        self.db.add(box)
        self.db.flush()
        return box

    def open_box(self, box_id: int) -> Box:
        box = self._get_box(box_id)
        if box.status != "active":
            raise HTTPException(status_code=409, detail="Box is not active")
        box.sealed = False
        return box

    def seal_box(self, box_id: int) -> Box:
        box = self._get_box(box_id)
        if box.status != "active":
            raise HTTPException(status_code=409, detail="Box is not active")
        # Session in tests uses autoflush=False; ensure box membership updates are persisted.
        self.db.flush()
        if not box.items:
            raise HTTPException(status_code=422, detail="Cannot seal empty box")
        box.sealed = True
        return box

    def add_item_by_qr(self, box_id: int, qr_code: str) -> dict:
        """
        Put a serialized item into a box.

        Allowed only for open boxes (sealed=false). For sealed boxes use open_box().
        """
        box = self._get_box(box_id)
        if box.status != "active":
            raise HTTPException(status_code=409, detail="Box is not active")
        if box.sealed:
            raise HTTPException(status_code=409, detail="Box is sealed; open it first")

        parsed = parse_qr(qr_code)
        if parsed.kind != "ITM":
            raise HTTPException(status_code=422, detail="Expected ITM QR")
        q = self.db.query(ProductItem).filter(ProductItem.uuid == parsed.uuid)
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            q = q.with_for_update()
        item = q.first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        if item.status not in {"receiving", "in_stock"}:
            raise HTTPException(status_code=409, detail="Item status does not allow boxing")
        if item.product_id != box.product_id or item.lot_id != box.lot_id:
            raise HTTPException(status_code=422, detail="Item product/lot does not match box")
        if item.location_id != box.location_id:
            raise HTTPException(status_code=409, detail="Item is in a different location")
        if item.box_id is not None and item.box_id != box.id:
            raise HTTPException(status_code=409, detail="Item is already in another box")
        item.box_id = box.id
        self.db.flush()
        return {"box_id": box.id, "product_item_id": item.id}

    def list_box_labels(self, box_id: int) -> list[str]:
        box = self._get_box(box_id)
        return [box.qr_code]

    def _get_box(self, box_id: int) -> Box:
        box = self.db.query(Box).get(box_id)
        if not box:
            raise HTTPException(status_code=404, detail="Box not found")
        return box
