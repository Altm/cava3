from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import (
    InventoryDoc,
    InventoryItem,
    ProductItem,
    StockLot,
    Receipt,
    Box,
)
from app.services.serial_qr import parse_qr
from app.services.serial_stock import SerialStockLedger


class InventoryService:
    """Inventory counting for serialized items: start(expected) -> scan -> close(missing->lost)."""

    def __init__(self, db: Session):
        self.db = db
        self.stock = SerialStockLedger(db)

    def create(self, location_id: int, created_by_user_id: int | None = None) -> InventoryDoc:
        doc = InventoryDoc(location_id=location_id, status="draft", created_by_user_id=created_by_user_id)
        self.db.add(doc)
        self.db.flush()
        return doc

    def start(self, inventory_doc_id: int) -> dict:
        """
        Build expected list: all in_stock items in location from posted receipts.
        """
        doc = self._get_doc(inventory_doc_id)
        if doc.status != "draft":
            raise HTTPException(status_code=409, detail="Inventory doc is not in draft state")

        items = (
            self.db.query(ProductItem.id)
            .join(StockLot, StockLot.id == ProductItem.lot_id)
            .join(Receipt, Receipt.id == StockLot.receipt_id)
            .filter(
                ProductItem.location_id == doc.location_id,
                ProductItem.status == "in_stock",
                Receipt.status == "posted",
            )
            .all()
        )
        if not items:
            doc.status = "counting"
            return {"inventory_doc_id": doc.id, "expected": 0}

        now = datetime.utcnow()
        to_add = [InventoryItem(inventory_doc_id=doc.id, product_item_id=item_id, state="expected") for (item_id,) in items]
        self.db.add_all(to_add)
        doc.status = "counting"
        doc.updated_at = now
        # Tests use autoflush=False; persist expected rows for subsequent scans.
        self.db.flush()
        return {"inventory_doc_id": doc.id, "expected": len(to_add)}

    def scan(self, inventory_doc_id: int, qr_code: str) -> dict:
        doc = self._get_doc(inventory_doc_id)
        if doc.status != "counting":
            raise HTTPException(status_code=409, detail="Inventory doc is not in counting state")

        parsed = parse_qr(qr_code)
        if parsed.kind == "ITM":
            result = self._scan_item(doc, parsed.uuid)
        else:
            result = self._scan_box(doc, parsed.uuid)
        # Tests use autoflush=False; persist scan state before further operations.
        self.db.flush()
        return result

    def close(self, inventory_doc_id: int) -> dict:
        """
        Close inventory (variant A): all expected not scanned become missing and items become lost.
        """
        doc = self._get_doc(inventory_doc_id)
        if doc.status != "counting":
            raise HTTPException(status_code=409, detail="Inventory doc is not in counting state")

        now = datetime.utcnow()
        missing = (
            self.db.query(InventoryItem)
            .filter(InventoryItem.inventory_doc_id == doc.id, InventoryItem.state == "expected")
            .all()
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            missing = (
                self.db.query(InventoryItem)
                .filter(InventoryItem.inventory_doc_id == doc.id, InventoryItem.state == "expected")
                .with_for_update()
                .all()
            )
        missing_item_ids = [mi.product_item_id for mi in missing]
        for mi in missing:
            mi.state = "missing"

        # Apply loss to product_item and aggregated stock
        by_product: dict[int, int] = {}
        box_detach_counts: dict[int, int] = {}
        if missing_item_ids:
            items = (
                self.db.query(ProductItem)
                .filter(ProductItem.id.in_(missing_item_ids))
                .all()
            )
            if self.db.bind and self.db.bind.dialect.name == "postgresql":
                items = (
                    self.db.query(ProductItem)
                    .filter(ProductItem.id.in_(missing_item_ids))
                    .with_for_update()
                    .all()
                )
            for item in items:
                if item.status != "in_stock" or item.location_id != doc.location_id:
                    continue
                if item.box_id is not None:
                    box_detach_counts[item.box_id] = box_detach_counts.get(item.box_id, 0) + 1
                item.status = "lost"
                item.lost_reason = "missing_inventory"
                item.lost_doc_type = "inventory"
                item.lost_doc_id = doc.id
                by_product[item.product_id] = by_product.get(item.product_id, 0) + 1

        if box_detach_counts:
            boxes = self.db.query(Box).filter(Box.id.in_(box_detach_counts.keys())).all()
            for box in boxes:
                detached = box_detach_counts.get(box.id, 0)
                if detached > 0:
                    box.quantity = max(0, int(box.quantity) - detached)

        for product_id, count in by_product.items():
            self.stock.adjust_base_units(doc.location_id, product_id, -count)

        doc.status = "closed"
        doc.closed_at = now
        # Tests run with autoflush=False; persist close results for read-after-write handlers.
        self.db.flush()
        return {"inventory_doc_id": doc.id, "missing": len(missing_item_ids)}

    # ---- internals ----

    def _scan_item(self, doc: InventoryDoc, item_uuid) -> dict:
        item = self.db.query(ProductItem).filter(ProductItem.uuid == item_uuid).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        if item.location_id != doc.location_id or item.status != "in_stock":
            raise HTTPException(status_code=409, detail="Item not eligible for this inventory location")

        row = (
            self.db.query(InventoryItem)
            .filter(InventoryItem.inventory_doc_id == doc.id, InventoryItem.product_item_id == item.id)
            .first()
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            row = (
                self.db.query(InventoryItem)
                .filter(InventoryItem.inventory_doc_id == doc.id, InventoryItem.product_item_id == item.id)
                .with_for_update()
                .first()
            )
        now = datetime.utcnow()
        if row:
            row.state = "scanned"
            row.scanned_at = now
            return {"inventory_doc_id": doc.id, "scanned_product_item_id": item.id, "state": "scanned"}

        # unexpected item (not in expected list)
        unexpected = InventoryItem(inventory_doc_id=doc.id, product_item_id=item.id, state="unexpected", scanned_at=now)
        self.db.add(unexpected)
        return {"inventory_doc_id": doc.id, "scanned_product_item_id": item.id, "state": "unexpected"}

    def _scan_box(self, doc: InventoryDoc, box_uuid) -> dict:
        box = self.db.query(Box).filter(Box.uuid == box_uuid).first()
        if not box or box.status != "active":
            raise HTTPException(status_code=404, detail="Box not found")
        if box.location_id != doc.location_id:
            has_expected_here = (
                self.db.query(InventoryItem.id)
                .join(ProductItem, ProductItem.id == InventoryItem.product_item_id)
                .filter(
                    InventoryItem.inventory_doc_id == doc.id,
                    InventoryItem.state == "expected",
                    ProductItem.box_id == box.id,
                    ProductItem.location_id == doc.location_id,
                    ProductItem.status == "in_stock",
                )
                .first()
                is not None
            )
            if not has_expected_here:
                raise HTTPException(status_code=409, detail="Box is in a different location")
            box.location_id = doc.location_id

        now = datetime.utcnow()
        # Mark all expected items in this box as scanned
        rows = (
            self.db.query(InventoryItem)
            .join(ProductItem, ProductItem.id == InventoryItem.product_item_id)
            .filter(
                InventoryItem.inventory_doc_id == doc.id,
                InventoryItem.state == "expected",
                ProductItem.box_id == box.id,
                ProductItem.location_id == doc.location_id,
                ProductItem.status == "in_stock",
            )
            .all()
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            rows = (
                self.db.query(InventoryItem)
                .join(ProductItem, ProductItem.id == InventoryItem.product_item_id)
                .filter(
                    InventoryItem.inventory_doc_id == doc.id,
                    InventoryItem.state == "expected",
                    ProductItem.box_id == box.id,
                    ProductItem.location_id == doc.location_id,
                    ProductItem.status == "in_stock",
                )
                .with_for_update()
                .all()
            )
        for row in rows:
            row.state = "scanned"
            row.scanned_at = now
        return {"inventory_doc_id": doc.id, "scanned_in_box": len(rows), "box_id": box.id}

    def _get_doc(self, inventory_doc_id: int) -> InventoryDoc:
        doc = self.db.get(InventoryDoc, inventory_doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Inventory doc not found")
        return doc
