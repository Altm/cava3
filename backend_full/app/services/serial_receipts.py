from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.models import Receipt, ReceiptLine, StockLot, ProductItem, Product, Unit, ProductUnit
from app.services.serial_stock import SerialStockLedger


@dataclass(frozen=True)
class GenerateResult:
    lots_created: int
    items_created: int


class ReceiptService:
    """Receipt lifecycle for serialized items (generate -> post -> void)."""

    def __init__(self, db: Session):
        self.db = db
        self.stock = SerialStockLedger(db)

    def create(self, to_location_id: int, created_by_user_id: int | None = None) -> Receipt:
        receipt = Receipt(to_location_id=to_location_id, status="draft", created_by_user_id=created_by_user_id)
        self.db.add(receipt)
        self.db.flush()
        return receipt

    def add_line(
        self,
        receipt_id: int,
        product_id: int,
        qty: Decimal,
        unit_id: int,
        supplier_lot_number: str | None = None,
    ) -> ReceiptLine:
        receipt = self._get_receipt(receipt_id)
        if receipt.status not in {"draft"}:
            raise HTTPException(status_code=409, detail="Receipt is not editable")
        if qty <= 0:
            raise HTTPException(status_code=422, detail="Quantity must be positive")
        line = ReceiptLine(
            receipt_id=receipt.id,
            product_id=product_id,
            qty=qty,
            unit_id=unit_id,
            supplier_lot_number=supplier_lot_number,
        )
        self.db.add(line)
        self.db.flush()
        return line

    def generate(self, receipt_id: int) -> GenerateResult:
        """
        Generate lots and serialized items for each receipt line.

        Items are created in status `receiving` and become `in_stock` only after `post()`.
        """
        receipt = self._get_receipt(receipt_id)
        if receipt.status != "draft":
            raise HTTPException(status_code=409, detail="Receipt is not in draft state")
        if not receipt.lines:
            raise HTTPException(status_code=422, detail="Receipt has no lines")

        total_items = 0
        lots_created = 0

        for line in receipt.lines:
            product = self._get_product(line.product_id)
            self._assert_product_is_serial(product)
            qty_base = self._to_base_discrete_units(product.id, line.unit_id, Decimal(line.qty))
            if qty_base <= 0:
                raise HTTPException(status_code=422, detail="Line quantity too small")

            lot = StockLot(product_id=product.id, receipt_id=receipt.id, supplier_lot_number=line.supplier_lot_number)
            self.db.add(lot)
            self.db.flush()  # get lot.id
            lots_created += 1

            items = [
                ProductItem(
                    product_id=product.id,
                    lot_id=lot.id,
                    location_id=receipt.to_location_id,
                    status="receiving",
                )
                for _ in range(qty_base)
            ]
            self.db.add_all(items)
            total_items += qty_base

        receipt.status = "generated"
        self.db.flush()
        return GenerateResult(lots_created=lots_created, items_created=total_items)

    def post(self, receipt_id: int) -> dict:
        """
        Confirm receipt: items become available and aggregated stock is increased.
        """
        receipt = self._get_receipt(receipt_id)
        if receipt.status != "generated":
            raise HTTPException(status_code=409, detail="Receipt is not in generated state")

        # Move items receiving -> in_stock and update aggregated stock in one transaction.
        q = (
            self.db.query(ProductItem)
            .join(StockLot, StockLot.id == ProductItem.lot_id)
            .filter(StockLot.receipt_id == receipt.id, ProductItem.status == "receiving")
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            q = q.with_for_update()
        items = q.all()
        if not items:
            raise HTTPException(status_code=409, detail="No items to post")

        counts_by_product: dict[int, int] = {}
        for item in items:
            item.status = "in_stock"
            counts_by_product[item.product_id] = counts_by_product.get(item.product_id, 0) + 1

        for product_id, count in counts_by_product.items():
            self.stock.adjust_base_units(receipt.to_location_id, product_id, count)

        receipt.status = "posted"
        return {"receipt_id": receipt.id, "posted_items": len(items)}

    def void(self, receipt_id: int) -> dict:
        """
        Cancel receipt (variant A): invalidate generated QR by setting items to `voided`.

        Allowed only if generated items were not moved/sold/damaged/reserved in other docs.
        """
        receipt = self._get_receipt(receipt_id)
        if receipt.status == "void":
            return {"receipt_id": receipt.id, "status": "void"}
        if receipt.status not in {"draft", "generated", "posted"}:
            raise HTTPException(status_code=409, detail="Receipt cannot be voided in current state")

        items_q = (
            self.db.query(ProductItem)
            .join(StockLot, StockLot.id == ProductItem.lot_id)
            .filter(StockLot.receipt_id == receipt.id)
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            items_q = items_q.with_for_update()
        items = items_q.all()
        if not items:
            receipt.status = "void"
            return {"receipt_id": receipt.id, "voided_items": 0}

        # Block void if any item already used in other processes.
        for item in items:
            if item.status not in {"receiving", "in_stock", "voided"}:
                raise HTTPException(status_code=409, detail="Receipt items already moved or disposed")
            if item.reserved_transfer_doc_id is not None:
                raise HTTPException(status_code=409, detail="Receipt items are reserved in transfer")

        # Fast checks (inventory_item, transfer_item)
        transfer_item_exists = (
            self.db.execute(
                text(
                    """
                SELECT 1
                FROM transfer_item ti
                JOIN product_item pi ON pi.id = ti.product_item_id
                JOIN stock_lot sl ON sl.id = pi.lot_id
                WHERE sl.receipt_id = :rid
                LIMIT 1
                    """
                ),
                {"rid": receipt.id},
            ).first()
            is not None
        )
        if transfer_item_exists:
            raise HTTPException(status_code=409, detail="Receipt items already linked to transfer")

        inventory_item_exists = (
            self.db.execute(
                text(
                    """
                SELECT 1
                FROM inventory_item ii
                JOIN product_item pi ON pi.id = ii.product_item_id
                JOIN stock_lot sl ON sl.id = pi.lot_id
                WHERE sl.receipt_id = :rid
                LIMIT 1
                    """
                ),
                {"rid": receipt.id},
            ).first()
            is not None
        )
        if inventory_item_exists:
            raise HTTPException(status_code=409, detail="Receipt items already linked to inventory")

        # void boxes belonging to receipt lots
        self.db.execute(
            text(
                """
            UPDATE box
            SET status = 'voided'
            WHERE lot_id IN (SELECT id FROM stock_lot WHERE receipt_id = :rid)
                """
            ),
            {"rid": receipt.id},
        )

        counts_by_product: dict[int, int] = {}
        for item in items:
            if item.status == "in_stock":
                counts_by_product[item.product_id] = counts_by_product.get(item.product_id, 0) + 1
            item.status = "voided"
            item.reserved_transfer_doc_id = None
            item.reserved_at = None
            item.box_id = None

        # If receipt was posted, compensate aggregated stock for items that were in_stock
        if receipt.status == "posted":
            for product_id, count in counts_by_product.items():
                self.stock.adjust_base_units(receipt.to_location_id, product_id, -count)

        receipt.status = "void"
        return {"receipt_id": receipt.id, "voided_items": len(items)}

    def list_item_labels(self, receipt_id: int) -> list[str]:
        receipt = self._get_receipt(receipt_id)
        qr_rows = (
            self.db.query(ProductItem.qr_code)
            .join(StockLot, StockLot.id == ProductItem.lot_id)
            .filter(StockLot.receipt_id == receipt.id)
            .order_by(ProductItem.id.asc())
            .all()
        )
        return [r[0] for r in qr_rows]

    def _get_receipt(self, receipt_id: int) -> Receipt:
        receipt = self.db.query(Receipt).get(receipt_id)
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        return receipt

    def _get_product(self, product_id: int) -> Product:
        product = self.db.query(Product).get(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    def _assert_product_is_serial(self, product: Product) -> None:
        unit = self.db.query(Unit).get(product.base_unit_id)
        if not unit or not unit.is_discrete:
            raise HTTPException(status_code=422, detail="Product base unit is not discrete")

    def _to_base_discrete_units(self, product_id: int, unit_id: int, qty: Decimal) -> int:
        """
        Convert input quantity to base units using product_unit ratio.

        For serialized processes we require the result to be an integer.
        """
        pu = (
            self.db.query(ProductUnit)
            .filter(ProductUnit.product_id == product_id, ProductUnit.unit_id == unit_id)
            .first()
        )
        if not pu:
            raise HTTPException(status_code=422, detail="Missing product unit conversion")
        ratio = Decimal(str(pu.ratio_to_base))
        qty_base = qty * ratio
        if qty_base != qty_base.to_integral_value():
            raise HTTPException(status_code=422, detail="Quantity must be integer in base units for serialized receipt")
        return int(qty_base)
