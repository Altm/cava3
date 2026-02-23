from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import (
    TransferDoc,
    TransferLine,
    TransferItem,
    ProductItem,
    ProductItemPour,
    Box,
    StockLot,
    Receipt,
    Product,
    Unit,
)
from app.services.serial_qr import parse_qr
from app.services.serial_stock import SerialStockLedger


ScanMode = Literal["picking", "receiving"]


@dataclass(frozen=True)
class PlanResult:
    transfer_line_id: int
    planned_items: int


class TransferService:
    """Transfer workflow for serialized items: plan -> pick(scan) -> receive(scan) -> close(loss)."""

    def __init__(self, db: Session):
        self.db = db
        self.stock = SerialStockLedger(db)

    def create(self, from_location_id: int, to_location_id: int, created_by_user_id: int | None = None) -> TransferDoc:
        doc = TransferDoc(
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            status="draft",
            created_by_user_id=created_by_user_id,
        )
        self.db.add(doc)
        self.db.flush()
        return doc

    def plan_fifo(self, transfer_doc_id: int, product_id: int, qty_base: int) -> PlanResult:
        """
        Create a transfer line and reserve concrete ProductItem rows (FIFO).

        Reservation is stored on ProductItem.reserved_transfer_doc_id to guarantee exclusivity.
        """
        doc = self._get_doc(transfer_doc_id)
        if doc.status not in {"draft", "picking"}:
            raise HTTPException(status_code=409, detail="Transfer is not editable")
        if qty_base <= 0:
            raise HTTPException(status_code=422, detail="qty_base must be positive")

        product = self._get_product(product_id)
        self._assert_product_is_serial(product)

        line = TransferLine(transfer_doc_id=doc.id, product_id=product_id, qty_base=qty_base, pick_policy="fifo")
        self.db.add(line)
        self.db.flush()

        items = self._select_available_items_fifo(doc, product_id, qty_base)
        if len(items) != qty_base:
            raise HTTPException(status_code=409, detail="Not enough serialized stock to plan transfer")

        now = datetime.utcnow()
        for item in items:
            item.reserved_transfer_doc_id = doc.id
            item.reserved_at = now
            self.db.add(
                TransferItem(
                    transfer_line_id=line.id,
                    product_item_id=item.id,
                    state="planned",
                    reserved_at=now,
                )
            )

        doc.status = "picking"
        # Tests use autoflush=False; ensure planned transfer_item rows exist for subsequent scans.
        self.db.flush()
        return PlanResult(transfer_line_id=line.id, planned_items=len(items))

    def remove_planned_item(self, transfer_doc_id: int, product_item_id: int) -> dict:
        """Remove a concrete planned item from transfer (manual edit): state=removed and reservation cleared."""
        doc = self._get_doc(transfer_doc_id)
        if doc.status not in {"draft", "picking"}:
            raise HTTPException(status_code=409, detail="Transfer is not editable")

        ti = (
            self.db.query(TransferItem)
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(TransferLine.transfer_doc_id == doc.id, TransferItem.product_item_id == product_item_id)
            .first()
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            ti = (
                self.db.query(TransferItem)
                .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
                .filter(TransferLine.transfer_doc_id == doc.id, TransferItem.product_item_id == product_item_id)
                .with_for_update()
                .first()
            )
        if not ti:
            raise HTTPException(status_code=404, detail="Transfer item not found")
        if ti.state != "planned":
            raise HTTPException(status_code=409, detail="Only planned items can be removed")
        ti.state = "removed"

        item = self.db.query(ProductItem).get(product_item_id)
        if item and item.reserved_transfer_doc_id == doc.id and item.status == "in_stock":
            item.reserved_transfer_doc_id = None
            item.reserved_at = None
        return {"transfer_doc_id": doc.id, "removed_product_item_id": product_item_id}

    def scan(self, transfer_doc_id: int, qr_code: str, mode: ScanMode) -> dict:
        """
        Scan ITM or BOX QR for picking (warehouse) or receiving (bar).

        Picking:
        - ITM: marks the planned item picked; unplanned valid ITM triggers replacement.
        - BOX: picks planned items from the box; partial from sealed => open box and detach picked items.

        Receiving:
        - ITM: moves item to bar (location_id), status in_stock.
        - BOX: receives all in_transit items in that box for this transfer.
        """
        doc = self._get_doc(transfer_doc_id)
        parsed = parse_qr(qr_code)
        if mode not in {"picking", "receiving"}:
            raise HTTPException(status_code=422, detail="Invalid scan mode")

        if parsed.kind == "ITM":
            result = self._scan_item(doc, parsed.uuid, mode)
        else:
            result = self._scan_box(doc, parsed.uuid, mode)
        # Tests use autoflush=False; make scan effects visible to subsequent queries (ship/close).
        self.db.flush()
        return result

    def ship(self, transfer_doc_id: int) -> dict:
        """Move transfer to shipped. Requires no remaining planned items."""
        doc = self._get_doc(transfer_doc_id)
        if doc.status != "picking":
            raise HTTPException(status_code=409, detail="Transfer is not in picking state")
        remaining = (
            self.db.query(TransferItem.id)
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(TransferLine.transfer_doc_id == doc.id, TransferItem.state == "planned")
            .first()
        )
        if remaining:
            raise HTTPException(status_code=409, detail="Transfer has remaining planned items")
        doc.status = "shipped"
        return {"transfer_doc_id": doc.id, "status": doc.status}

    def close(self, transfer_doc_id: int) -> dict:
        """
        Close transfer in bar (variant A): anything picked but not received becomes lost_in_transit.
        """
        doc = self._get_doc(transfer_doc_id)
        if doc.status != "shipped":
            raise HTTPException(status_code=409, detail="Transfer must be shipped before close")

        # ensure no planned remain
        planned_exists = (
            self.db.query(TransferItem.id)
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(TransferLine.transfer_doc_id == doc.id, TransferItem.state == "planned")
            .first()
            is not None
        )
        if planned_exists:
            raise HTTPException(status_code=409, detail="Transfer has remaining planned items")

        lost_ids = []
        q = (
            self.db.query(TransferItem)
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(TransferLine.transfer_doc_id == doc.id, TransferItem.state == "picked", TransferItem.received_at.is_(None))
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            q = q.with_for_update()
        picked_not_received = q.all()
        for ti in picked_not_received:
            item = self.db.query(ProductItem).get(ti.product_item_id)
            if not item:
                continue
            if item.box_id is not None:
                box = self.db.query(Box).get(item.box_id)
                if box and box.quantity > 0:
                    box.quantity -= 1
            item.status = "lost"
            item.lost_reason = "lost_in_transit"
            item.lost_doc_type = "transfer"
            item.lost_doc_id = doc.id
            item.reserved_transfer_doc_id = None
            item.reserved_at = None
            item.box_id = None
            lost_ids.append(item.id)

        doc.status = "closed"
        return {"transfer_doc_id": doc.id, "lost_items": len(lost_ids)}

    # ---- internals ----

    def _select_available_items_fifo(self, doc: TransferDoc, product_id: int, qty_base: int) -> list[ProductItem]:
        """
        FIFO selection by (lot.received_at, item.created_at, item.id), with box-aware preference:
        - first, full sealed boxes (if they fit completely in remaining qty)
        - then item-level FIFO for the remainder
        - partially poured items are excluded
        """
        if qty_base <= 0:
            return []

        selected: list[ProductItem] = []
        selected_ids: set[int] = set()
        remaining = qty_base

        boxes_q = (
            self.db.query(Box)
            .join(StockLot, StockLot.id == Box.lot_id)
            .join(Receipt, Receipt.id == StockLot.receipt_id)
            .filter(
                Box.location_id == doc.from_location_id,
                Box.product_id == product_id,
                Box.status == "active",
                Box.sealed.is_(True),
                Box.quantity > 0,
                Receipt.status == "posted",
            )
            .order_by(StockLot.received_at.asc(), Box.created_at.asc(), Box.id.asc())
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            boxes_q = boxes_q.with_for_update(skip_locked=True)
        sealed_boxes = boxes_q.all()

        for box in sealed_boxes:
            if remaining <= 0:
                break
            box_qty = int(box.quantity or 0)
            if box_qty <= 0 or box_qty > remaining:
                continue

            box_items_q = (
                self.db.query(ProductItem)
                .outerjoin(ProductItemPour, ProductItemPour.product_item_id == ProductItem.id)
                .filter(
                    ProductItem.box_id == box.id,
                    ProductItem.location_id == doc.from_location_id,
                    ProductItem.product_id == product_id,
                    ProductItem.status == "in_stock",
                    ProductItem.reserved_transfer_doc_id.is_(None),
                    (ProductItemPour.product_item_id.is_(None) | (ProductItemPour.used_units == 0)),
                )
                .order_by(ProductItem.id.asc())
                .limit(box_qty)
            )
            if self.db.bind and self.db.bind.dialect.name == "postgresql":
                box_items_q = box_items_q.with_for_update(of=ProductItem, skip_locked=True)
            box_items = box_items_q.all()
            if len(box_items) != box_qty:
                continue

            for box_item in box_items:
                if box_item.id in selected_ids:
                    continue
                selected.append(box_item)
                selected_ids.add(box_item.id)
            remaining -= len(box_items)

        if remaining > 0:
            items_q = (
                self.db.query(ProductItem)
                .join(StockLot, StockLot.id == ProductItem.lot_id)
                .join(Receipt, Receipt.id == StockLot.receipt_id)
                .outerjoin(ProductItemPour, ProductItemPour.product_item_id == ProductItem.id)
                .filter(
                    ProductItem.location_id == doc.from_location_id,
                    ProductItem.product_id == product_id,
                    ProductItem.status == "in_stock",
                    ProductItem.reserved_transfer_doc_id.is_(None),
                    Receipt.status == "posted",
                    (ProductItemPour.product_item_id.is_(None) | (ProductItemPour.used_units == 0)),
                )
                .order_by(StockLot.received_at.asc(), ProductItem.created_at.asc(), ProductItem.id.asc())
            )
            if selected_ids:
                items_q = items_q.filter(~ProductItem.id.in_(selected_ids))
            if self.db.bind and self.db.bind.dialect.name == "postgresql":
                items_q = items_q.with_for_update(of=ProductItem, skip_locked=True)
            selected.extend(items_q.limit(remaining).all())

        return selected

    def _scan_item(self, doc: TransferDoc, item_uuid, mode: ScanMode) -> dict:
        q = self.db.query(ProductItem).filter(ProductItem.uuid == item_uuid)
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            q = q.with_for_update()
        item = q.first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        if mode == "picking":
            return self._pick_item(doc, item)
        return self._receive_item(doc, item)

    def _scan_box(self, doc: TransferDoc, box_uuid, mode: ScanMode) -> dict:
        q = self.db.query(Box).filter(Box.uuid == box_uuid)
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            q = q.with_for_update()
        box = q.first()
        if not box or box.status != "active":
            raise HTTPException(status_code=404, detail="Box not found")
        if mode == "picking":
            return self._pick_box(doc, box)
        return self._receive_box(doc, box)

    def _pick_item(self, doc: TransferDoc, item: ProductItem) -> dict:
        if doc.status not in {"picking"}:
            raise HTTPException(status_code=409, detail="Transfer is not in picking state")
        if item.status != "in_stock":
            raise HTTPException(status_code=409, detail="Item is not available for picking")
        if item.location_id != doc.from_location_id:
            raise HTTPException(status_code=409, detail="Item is in a different location")
        pour = self.db.query(ProductItemPour).filter(ProductItemPour.product_item_id == item.id).first()
        if pour and pour.used_units > 0 and pour.used_units < pour.total_units:
            raise HTTPException(status_code=409, detail="Partially used item cannot be transferred")

        # Find transfer_item for this item in this doc
        ti = (
            self.db.query(TransferItem)
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(TransferLine.transfer_doc_id == doc.id, TransferItem.product_item_id == item.id)
            .first()
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            ti = (
                self.db.query(TransferItem)
                .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
                .filter(TransferLine.transfer_doc_id == doc.id, TransferItem.product_item_id == item.id)
                .with_for_update()
                .first()
            )

        if ti and ti.state == "planned":
            return self._mark_picked(doc, item, ti, detach_from_box=self._should_detach_item_on_pick(item))

        # Replacement flow: item must be unreserved
        if item.reserved_transfer_doc_id not in {None, doc.id}:
            raise HTTPException(status_code=409, detail="Item is reserved by another transfer")
        if item.reserved_transfer_doc_id is None:
            # Replace one remaining planned item in same product line
            repl = self._replace_planned_with_scanned(doc, item)
            return repl

        raise HTTPException(status_code=409, detail="Item already processed for this transfer")

    def _replace_planned_with_scanned(self, doc: TransferDoc, item: ProductItem) -> dict:
        line = (
            self.db.query(TransferLine)
            .filter(TransferLine.transfer_doc_id == doc.id, TransferLine.product_id == item.product_id)
            .first()
        )
        if not line:
            raise HTTPException(status_code=409, detail="No planned line for this product")

        to_remove = (
            self.db.query(TransferItem)
            .filter(TransferItem.transfer_line_id == line.id, TransferItem.state == "planned")
            .order_by(TransferItem.id.asc())
            .first()
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            to_remove = (
                self.db.query(TransferItem)
                .filter(TransferItem.transfer_line_id == line.id, TransferItem.state == "planned")
                .order_by(TransferItem.id.asc())
                .with_for_update()
                .first()
            )
        if not to_remove:
            raise HTTPException(status_code=409, detail="No remaining planned items to replace")

        removed_item = self.db.query(ProductItem).get(to_remove.product_item_id)
        if removed_item and removed_item.reserved_transfer_doc_id == doc.id and removed_item.status == "in_stock":
            removed_item.reserved_transfer_doc_id = None
            removed_item.reserved_at = None
        to_remove.state = "removed"

        now = datetime.utcnow()
        item.reserved_transfer_doc_id = doc.id
        item.reserved_at = now
        ti = TransferItem(
            transfer_line_id=line.id,
            product_item_id=item.id,
            state="picked",
            reserved_at=now,
            picked_at=now,
        )
        self.db.add(ti)
        return self._mark_picked(doc, item, ti, detach_from_box=self._should_detach_item_on_pick(item))

    def _should_detach_item_on_pick(self, item: ProductItem) -> bool:
        """
        If an item is picked from a sealed box and we are not moving the whole box,
        we must detach it (box_id=NULL) to avoid mixed box content across locations.
        """
        if not item.box_id:
            return False
        box = self.db.query(Box).get(item.box_id)
        return bool(box and box.sealed)

    def _mark_picked(self, doc: TransferDoc, item: ProductItem, ti: TransferItem, detach_from_box: bool) -> dict:
        now = datetime.utcnow()
        if detach_from_box and item.box_id:
            box = self.db.query(Box).get(item.box_id)
            if box and box.sealed:
                box.sealed = False
            if box and box.quantity > 0:
                box.quantity -= 1
            item.box_id = None
        ti.state = "picked"
        ti.picked_at = ti.picked_at or now
        item.reserved_transfer_doc_id = doc.id
        item.reserved_at = item.reserved_at or now
        item.status = "in_transit"
        # aggregated stock: leave warehouse availability immediately
        self.stock.adjust_base_units(doc.from_location_id, item.product_id, -1)
        return {"transfer_doc_id": doc.id, "picked_item_id": item.id}

    def _pick_box(self, doc: TransferDoc, box: Box) -> dict:
        if doc.status != "picking":
            raise HTTPException(status_code=409, detail="Transfer is not in picking state")
        if box.location_id != doc.from_location_id:
            raise HTTPException(status_code=409, detail="Box is in a different location")

        planned_items = (
            self.db.query(ProductItem, TransferItem)
            .join(TransferItem, TransferItem.product_item_id == ProductItem.id)
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(
                TransferLine.transfer_doc_id == doc.id,
                ProductItem.box_id == box.id,
                TransferItem.state == "planned",
                ProductItem.status == "in_stock",
            )
            .all()
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            planned_items = (
                self.db.query(ProductItem, TransferItem)
                .join(TransferItem, TransferItem.product_item_id == ProductItem.id)
                .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
                .filter(
                    TransferLine.transfer_doc_id == doc.id,
                    ProductItem.box_id == box.id,
                    TransferItem.state == "planned",
                    ProductItem.status == "in_stock",
                )
                .with_for_update()
                .all()
            )

        if not planned_items:
            raise HTTPException(status_code=409, detail="No planned items in this box to pick")

        total_in_stock_in_box = (
            self.db.query(ProductItem.id)
            .filter(ProductItem.box_id == box.id, ProductItem.status == "in_stock")
            .count()
        )
        partial = len(planned_items) < total_in_stock_in_box
        if partial and box.sealed:
            box.sealed = False

        picked = 0
        for item, ti in planned_items:
            # if partial pick, detach picked items from the box
            detach = partial
            self._mark_picked(doc, item, ti, detach_from_box=detach)
            picked += 1
        return {"transfer_doc_id": doc.id, "picked_items": picked, "box_id": box.id, "box_opened": partial}

    def _receive_item(self, doc: TransferDoc, item: ProductItem) -> dict:
        if doc.status not in {"shipped"}:
            raise HTTPException(status_code=409, detail="Transfer is not in receiving state")
        if item.reserved_transfer_doc_id != doc.id:
            raise HTTPException(status_code=409, detail="Item is not reserved for this transfer")
        if item.status != "in_transit":
            raise HTTPException(status_code=409, detail="Item is not in transit")

        ti = (
            self.db.query(TransferItem)
            .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
            .filter(TransferLine.transfer_doc_id == doc.id, TransferItem.product_item_id == item.id, TransferItem.state == "picked")
            .first()
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            ti = (
                self.db.query(TransferItem)
                .join(TransferLine, TransferLine.id == TransferItem.transfer_line_id)
                .filter(TransferLine.transfer_doc_id == doc.id, TransferItem.product_item_id == item.id, TransferItem.state == "picked")
                .with_for_update()
                .first()
            )
        if not ti:
            raise HTTPException(status_code=409, detail="Item is not picked in this transfer")

        now = datetime.utcnow()
        item.location_id = doc.to_location_id
        item.status = "in_stock"
        item.reserved_transfer_doc_id = None
        item.reserved_at = None
        if item.box_id is not None:
            box = self.db.query(Box).get(item.box_id)
            if box and box.location_id != doc.to_location_id:
                box.location_id = doc.to_location_id
        ti.received_at = now
        # aggregated stock: bar availability increases on receipt
        self.stock.adjust_base_units(doc.to_location_id, item.product_id, 1)
        return {"transfer_doc_id": doc.id, "received_item_id": item.id}

    def _receive_box(self, doc: TransferDoc, box: Box) -> dict:
        if doc.status != "shipped":
            raise HTTPException(status_code=409, detail="Transfer is not in receiving state")
        # Receive only items still associated with this box and reserved for this doc.
        items = (
            self.db.query(ProductItem)
            .filter(
                ProductItem.box_id == box.id,
                ProductItem.reserved_transfer_doc_id == doc.id,
                ProductItem.status == "in_transit",
            )
            .all()
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            items = (
                self.db.query(ProductItem)
                .filter(
                    ProductItem.box_id == box.id,
                    ProductItem.reserved_transfer_doc_id == doc.id,
                    ProductItem.status == "in_transit",
                )
                .with_for_update()
                .all()
            )
        if not items:
            raise HTTPException(status_code=409, detail="No in-transit items in this box for this transfer")

        received = 0
        for item in items:
            self._receive_item(doc, item)
            received += 1

        # if all remaining items in box are now in bar, update box location
        remaining_in_transit = (
            self.db.query(ProductItem.id)
            .filter(ProductItem.box_id == box.id, ProductItem.status == "in_transit")
            .first()
            is not None
        )
        if not remaining_in_transit:
            box.location_id = doc.to_location_id
        return {"transfer_doc_id": doc.id, "received_items": received, "box_id": box.id}

    def _get_doc(self, transfer_doc_id: int) -> TransferDoc:
        doc = self.db.query(TransferDoc).get(transfer_doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Transfer not found")
        return doc

    def _get_product(self, product_id: int) -> Product:
        product = self.db.query(Product).get(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    def _assert_product_is_serial(self, product: Product) -> None:
        unit = self.db.query(Unit).get(product.base_unit_id)
        if not unit or not unit.is_discrete:
            raise HTTPException(status_code=422, detail="Product base unit is not discrete")
