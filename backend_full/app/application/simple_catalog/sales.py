from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.application.common.uow import AbstractUnitOfWork
from app.config import get_settings
from app.models import models
from app.schemas import simple as schemas
from app.security.hmac import _generate_hmac_signature
from app.services.serial_qr import parse_qr
from app.services.serial_stock import SerialStockLedger
from app.services.stock_service import StockService


@dataclass(frozen=True)
class SaleCheckoutCommand:
    payload: schemas.SaleCheckoutRequest
    user_id: int | None = None


@dataclass(frozen=True)
class ListSalesQuery:
    status: str | None
    location_id: int | None
    terminal_id: str | None
    date_from: datetime | None
    date_to: datetime | None
    limit: int


@dataclass(frozen=True)
class GetSaleQuery:
    sale_event_id: int


@dataclass(frozen=True)
class ConfirmSaleCommand:
    sale_event_id: int


@dataclass(frozen=True)
class SellProductCommand:
    payload: schemas.SaleRequest


@dataclass(frozen=True)
class SellWineGlassCommand:
    payload: schemas.SaleRequest


@dataclass(frozen=True)
class _ResolvedLine:
    kind: str
    product: models.Product
    quantity: Decimal
    unit_id: int
    unit_code: str
    unit_price: Decimal
    total_price: Decimal
    resolved_item_ids: list[int]
    resolved_box_id: int | None = None


class ListSalesHandler:
    def handle(self, query: ListSalesQuery, uow: AbstractUnitOfWork) -> list[schemas.SaleListItemOut]:
        db = uow.session
        query_builder = (
            db.query(
                models.SaleEvent,
                models.Terminal.terminal_id.label("terminal_public_id"),
                models.Location.name.label("location_name"),
            )
            .join(models.Terminal, models.Terminal.id == models.SaleEvent.terminal_id)
            .join(models.Location, models.Location.id == models.SaleEvent.location_id)
        )

        if query.status:
            query_builder = query_builder.filter(models.SaleEvent.status == query.status)
        if query.location_id is not None:
            query_builder = query_builder.filter(models.SaleEvent.location_id == query.location_id)
        if query.terminal_id:
            query_builder = query_builder.filter(models.Terminal.terminal_id == query.terminal_id)
        if query.date_from is not None:
            date_from = self._as_naive_utc(query.date_from)
            query_builder = query_builder.filter(models.SaleEvent.created_at >= date_from)
        if query.date_to is not None:
            date_to = self._as_naive_utc(query.date_to)
            query_builder = query_builder.filter(models.SaleEvent.created_at <= date_to)

        rows = (
            query_builder
            .order_by(models.SaleEvent.created_at.desc(), models.SaleEvent.id.desc())
            .limit(max(1, min(query.limit, 500)))
            .all()
        )
        if not rows:
            return []

        event_ids = [event.id for event, _, _ in rows]
        totals_rows = (
            db.query(
                models.SaleLine.sale_event_id,
                func.count(models.SaleLine.id),
                func.coalesce(func.sum(models.SaleLine.price), 0),
            )
            .filter(models.SaleLine.sale_event_id.in_(event_ids))
            .group_by(models.SaleLine.sale_event_id)
            .all()
        )
        totals_by_event_id: dict[int, tuple[int, Decimal]] = {}
        for sale_event_id, lines_count, total_amount in totals_rows:
            totals_by_event_id[int(sale_event_id)] = (int(lines_count or 0), Decimal(str(total_amount or 0)))

        result: list[schemas.SaleListItemOut] = []
        for sale_event, terminal_public_id, location_name in rows:
            lines_count, total_amount = totals_by_event_id.get(sale_event.id, (0, Decimal("0")))
            result.append(
                schemas.SaleListItemOut(
                    id=sale_event.id,
                    sale_id=sale_event.sale_id,
                    event_id=sale_event.event_id,
                    status=sale_event.status,
                    terminal_id=terminal_public_id,
                    location_id=sale_event.location_id,
                    location_name=location_name,
                    user_id=sale_event.user_id,
                    lines_count=lines_count,
                    total_amount=total_amount.quantize(Decimal("0.01")),
                    created_at=sale_event.created_at,
                    confirmed_at=sale_event.confirmed_at,
                )
            )
        return result

    @staticmethod
    def _as_naive_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)


class GetSaleHandler:
    def handle(self, query: GetSaleQuery, uow: AbstractUnitOfWork) -> schemas.SaleDetailOut:
        db = uow.session
        row = (
            db.query(
                models.SaleEvent,
                models.Terminal.terminal_id.label("terminal_public_id"),
                models.Location.name.label("location_name"),
            )
            .join(models.Terminal, models.Terminal.id == models.SaleEvent.terminal_id)
            .join(models.Location, models.Location.id == models.SaleEvent.location_id)
            .filter(models.SaleEvent.id == query.sale_event_id)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Sale not found")
        sale_event, terminal_public_id, location_name = row

        lines_rows = (
            db.query(
                models.SaleLine,
                models.Product.name.label("product_name"),
                models.Product.sku.label("product_sku"),
                models.Unit.code.label("unit_code"),
            )
            .join(models.Product, models.Product.id == models.SaleLine.product_id)
            .join(models.Unit, models.Unit.id == models.SaleLine.unit_id)
            .filter(models.SaleLine.sale_event_id == sale_event.id)
            .order_by(models.SaleLine.id.asc())
            .all()
        )
        detail_lines: list[schemas.SaleDetailLineOut] = []
        total_amount = Decimal("0")
        for sale_line, product_name, product_sku, unit_code in lines_rows:
            line_total = Decimal(str(sale_line.price or 0)).quantize(Decimal("0.01"))
            total_amount += line_total
            detail_lines.append(
                schemas.SaleDetailLineOut(
                    id=sale_line.id,
                    product_id=sale_line.product_id,
                    product_name=product_name,
                    product_sku=product_sku,
                    quantity=Decimal(str(sale_line.quantity)),
                    unit_id=sale_line.unit_id,
                    unit_code=unit_code,
                    currency=sale_line.currency,
                    line_total_amount=line_total,
                )
            )

        return schemas.SaleDetailOut(
            id=sale_event.id,
            sale_id=sale_event.sale_id,
            event_id=sale_event.event_id,
            status=sale_event.status,
            terminal_id=terminal_public_id,
            location_id=sale_event.location_id,
            location_name=location_name,
            user_id=sale_event.user_id,
            total_amount=total_amount.quantize(Decimal("0.01")),
            created_at=sale_event.created_at,
            confirmed_at=sale_event.confirmed_at,
            payload=sale_event.payload if isinstance(sale_event.payload, dict) else {},
            lines=detail_lines,
        )


class ConfirmSaleHandler:
    def handle(self, command: ConfirmSaleCommand, uow: AbstractUnitOfWork) -> schemas.SaleDetailOut:
        db = uow.session
        sale_event = db.query(models.SaleEvent).filter(models.SaleEvent.id == command.sale_event_id).first()
        if not sale_event:
            raise HTTPException(status_code=404, detail="Sale not found")
        if sale_event.status != "confirmed":
            sale_event.status = "confirmed"
            sale_event.confirmed_at = datetime.utcnow()
        return GetSaleHandler().handle(GetSaleQuery(sale_event_id=sale_event.id), uow)


class SalesCheckoutHandler:
    def __init__(self) -> None:
        self.settings = get_settings()

    def handle(self, command: SaleCheckoutCommand, uow: AbstractUnitOfWork) -> schemas.SaleCheckoutOut:
        if not command.payload.lines:
            raise HTTPException(status_code=422, detail="No sales lines provided")

        db = uow.session
        serial_stock = SerialStockLedger(db)
        stock_service = StockService(db)

        terminal = (
            db.query(models.Terminal)
            .filter(models.Terminal.terminal_id == self.settings.sales_terminal_id)
            .first()
        )
        if not terminal:
            raise HTTPException(status_code=422, detail="Configured sales terminal not found")

        resolved_lines: list[_ResolvedLine] = []
        for line in command.payload.lines:
            if line.kind == "product":
                resolved_lines.append(
                    self._handle_product_line(
                        db=db,
                        terminal=terminal,
                        line=line,
                        serial_stock=serial_stock,
                        stock_service=stock_service,
                    )
                )
                continue
            if line.kind == "item_qr":
                resolved_lines.append(
                    self._handle_item_qr_line(
                        db=db,
                        terminal=terminal,
                        line=line,
                        serial_stock=serial_stock,
                    )
                )
                continue
            if line.kind == "box_qr":
                resolved_lines.append(
                    self._handle_box_qr_line(
                        db=db,
                        terminal=terminal,
                        line=line,
                        serial_stock=serial_stock,
                    )
                )
                continue
            if line.kind == "glass":
                resolved_lines.append(
                    self._handle_glass_line(
                        db=db,
                        terminal=terminal,
                        line=line,
                        stock_service=stock_service,
                    )
                )
                continue
            raise HTTPException(status_code=422, detail=f"Unsupported sales line kind: {line.kind}")

        total_amount = sum((line.total_price for line in resolved_lines), Decimal("0"))
        now_utc = datetime.now(timezone.utc)
        sale_id = int(now_utc.timestamp() * 1000)
        effective_user_id = self._resolve_checkout_user_id(command.user_id)
        register_payload = self._build_register_payload(
            sale_id=sale_id,
            terminal_id=terminal.terminal_id,
            user_id=effective_user_id,
            sold_at=now_utc,
            lines=resolved_lines,
        )
        register_response = self._send_register_transactions_request(
            db=db,
            terminal=terminal,
            payload=register_payload,
        )

        return schemas.SaleCheckoutOut(
            sale_id=sale_id,
            terminal_id=terminal.terminal_id,
            location_id=terminal.location_id,
            total_amount=total_amount.quantize(Decimal("0.01")),
            lines=[
                schemas.SaleCheckoutResolvedLine(
                    kind=line.kind,
                    product_id=line.product.id,
                    product_name=line.product.name,
                    quantity=line.quantity,
                    unit_id=line.unit_id,
                    unit_code=line.unit_code,
                    unit_price=line.unit_price,
                    total_price=line.total_price,
                    resolved_item_ids=line.resolved_item_ids,
                    resolved_box_id=line.resolved_box_id,
                )
                for line in resolved_lines
            ],
            register_payload=register_payload,
            register_response=register_response,
        )

    def _handle_product_line(
        self,
        *,
        db: Session,
        terminal: models.Terminal,
        line: schemas.SaleCheckoutLineIn,
        serial_stock: SerialStockLedger,
        stock_service: StockService,
    ) -> _ResolvedLine:
        if line.product_id is None:
            raise HTTPException(status_code=422, detail="product_id is required for product line")
        quantity = self._positive_decimal(line.quantity, field_name="quantity")
        product = self._get_product(db, line.product_id)
        unit_id = line.unit_id or product.base_unit_id
        unit = self._get_unit(db, unit_id)
        ratio_to_base = self._ratio_to_base(db, product, unit_id)

        if self._is_serial_product(db, product):
            qty_base = quantity * ratio_to_base
            qty_base_int = self._to_int_base_units(qty_base)
            items = self._select_sellable_items_fifo(
                db=db,
                location_id=terminal.location_id,
                product_id=product.id,
                limit=qty_base_int,
            )
            if len(items) < qty_base_int:
                available = self._count_sellable_items(
                    db=db,
                    location_id=terminal.location_id,
                    product_id=product.id,
                )
                if available == 0 and self.settings.sales_allow_aggregate_fallback_for_serial:
                    stock_service.adjust_stock(
                        location_id=terminal.location_id,
                        product_id=product.id,
                        quantity=-quantity,
                        unit_id=unit_id,
                    )
                    sold_item_ids = []
                    unit_price = self._resolve_unit_price(
                        db=db,
                        location_id=terminal.location_id,
                        product=product,
                        unit_id=unit_id,
                        ratio_to_base=ratio_to_base,
                    )
                    total_price = (unit_price * quantity).quantize(Decimal("0.01"))
                    return _ResolvedLine(
                        kind="product",
                        product=product,
                        quantity=quantity,
                        unit_id=unit.id,
                        unit_code=unit.code,
                        unit_price=unit_price,
                        total_price=total_price,
                        resolved_item_ids=sold_item_ids,
                    )
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient serialized stock: requested={qty_base_int}, available={available}",
                )
            sold_item_ids: list[int] = []
            for item in items:
                self._sell_item(serial_stock, terminal.location_id, item, adjust_stock=True)
                sold_item_ids.append(item.id)
        else:
            stock_service.adjust_stock(
                location_id=terminal.location_id,
                product_id=product.id,
                quantity=-quantity,
                unit_id=unit_id,
            )
            sold_item_ids = []

        unit_price = self._resolve_unit_price(
            db=db,
            location_id=terminal.location_id,
            product=product,
            unit_id=unit_id,
            ratio_to_base=ratio_to_base,
        )
        total_price = (unit_price * quantity).quantize(Decimal("0.01"))
        return _ResolvedLine(
            kind="product",
            product=product,
            quantity=quantity,
            unit_id=unit.id,
            unit_code=unit.code,
            unit_price=unit_price,
            total_price=total_price,
            resolved_item_ids=sold_item_ids,
        )

    def _handle_item_qr_line(
        self,
        *,
        db: Session,
        terminal: models.Terminal,
        line: schemas.SaleCheckoutLineIn,
        serial_stock: SerialStockLedger,
    ) -> _ResolvedLine:
        qr_code = (line.qr_code or "").strip()
        if not qr_code:
            raise HTTPException(status_code=422, detail="qr_code is required for item_qr line")
        parsed = parse_qr(qr_code)
        if parsed.kind != "ITM":
            raise HTTPException(status_code=422, detail="Expected ITM QR for item_qr line")

        query_builder = db.query(models.ProductItem).filter(models.ProductItem.uuid == parsed.uuid)
        query_builder = self._with_row_lock(query_builder)
        item = query_builder.first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        self._assert_item_sellable(item=item, location_id=terminal.location_id)

        pour = (
            db.query(models.ProductItemPour)
            .filter(models.ProductItemPour.product_item_id == item.id)
            .first()
        )
        if pour and pour.glasses_sold > 0 and pour.glasses_sold < pour.glasses_total:
            raise HTTPException(status_code=409, detail="Item is partially poured and cannot be sold as whole")

        product = self._get_product(db, item.product_id)
        self._sell_item(serial_stock, terminal.location_id, item, adjust_stock=True)

        unit = self._get_unit(db, product.base_unit_id)
        unit_price = self._resolve_unit_price(
            db=db,
            location_id=terminal.location_id,
            product=product,
            unit_id=unit.id,
            ratio_to_base=Decimal("1"),
        )
        return _ResolvedLine(
            kind="item_qr",
            product=product,
            quantity=Decimal("1"),
            unit_id=unit.id,
            unit_code=unit.code,
            unit_price=unit_price,
            total_price=unit_price,
            resolved_item_ids=[item.id],
        )

    def _handle_box_qr_line(
        self,
        *,
        db: Session,
        terminal: models.Terminal,
        line: schemas.SaleCheckoutLineIn,
        serial_stock: SerialStockLedger,
    ) -> _ResolvedLine:
        if line.quantity is not None and Decimal(str(line.quantity)) != Decimal("1"):
            raise HTTPException(status_code=422, detail="Box sale supports quantity=1 only (whole box)")
        qr_code = (line.qr_code or "").strip()
        if not qr_code:
            raise HTTPException(status_code=422, detail="qr_code is required for box_qr line")
        parsed = parse_qr(qr_code)
        if parsed.kind != "BOX":
            raise HTTPException(status_code=422, detail="Expected BOX QR for box_qr line")

        box_query = db.query(models.Box).filter(models.Box.uuid == parsed.uuid)
        box_query = self._with_row_lock(box_query)
        box = box_query.first()
        if not box or box.status != "active":
            raise HTTPException(status_code=404, detail="Box not found")
        if box.location_id != terminal.location_id:
            raise HTTPException(status_code=409, detail="Box is in another location")

        items_query = (
            db.query(models.ProductItem)
            .filter(
                models.ProductItem.box_id == box.id,
                models.ProductItem.status == "in_stock",
            )
            .order_by(models.ProductItem.id.asc())
        )
        items_query = self._with_row_lock(items_query)
        items = items_query.all()
        if not items:
            raise HTTPException(status_code=409, detail="Box has no sellable items")

        for item in items:
            self._assert_item_sellable(item=item, location_id=terminal.location_id)
            if item.product_id != box.product_id:
                raise HTTPException(status_code=409, detail="Box contains mixed products")

        partial_pours_exist = (
            db.query(models.ProductItemPour.product_item_id)
            .filter(
                models.ProductItemPour.product_item_id.in_([item.id for item in items]),
                models.ProductItemPour.glasses_sold > 0,
                models.ProductItemPour.glasses_sold < models.ProductItemPour.glasses_total,
            )
            .first()
            is not None
        )
        if partial_pours_exist:
            raise HTTPException(status_code=409, detail="Box contains partially poured items")

        product = self._get_product(db, box.product_id)
        sold_item_ids: list[int] = []
        for item in items:
            self._sell_item(serial_stock, terminal.location_id, item, adjust_stock=True)
            sold_item_ids.append(item.id)

        qty_base = Decimal(len(items))
        package_unit = self._find_package_unit_by_size(db, product.id, len(items))
        if package_unit:
            unit_id = package_unit.unit_id
            quantity = Decimal("1")
            ratio_to_base = Decimal(str(package_unit.ratio_to_base))
        else:
            unit_id = product.base_unit_id
            quantity = qty_base
            ratio_to_base = Decimal("1")

        unit = self._get_unit(db, unit_id)
        unit_price = self._resolve_unit_price(
            db=db,
            location_id=terminal.location_id,
            product=product,
            unit_id=unit_id,
            ratio_to_base=ratio_to_base,
        )
        total_price = (unit_price * quantity).quantize(Decimal("0.01"))
        return _ResolvedLine(
            kind="box_qr",
            product=product,
            quantity=quantity,
            unit_id=unit.id,
            unit_code=unit.code,
            unit_price=unit_price,
            total_price=total_price,
            resolved_item_ids=sold_item_ids,
            resolved_box_id=box.id,
        )

    def _handle_glass_line(
        self,
        *,
        db: Session,
        terminal: models.Terminal,
        line: schemas.SaleCheckoutLineIn,
        stock_service: StockService,
    ) -> _ResolvedLine:
        if line.product_id is None:
            raise HTTPException(status_code=422, detail="product_id is required for glass line")
        product = self._get_product(db, line.product_id)
        glasses_requested = self._positive_integer_quantity(line.quantity, field_name="quantity")
        if not self._is_serial_product(db, product):
            raise HTTPException(status_code=422, detail="Glass sale is supported only for serialized products")

        target_item = None
        if line.item_qr_code:
            parsed_item = parse_qr(line.item_qr_code.strip())
            if parsed_item.kind != "ITM":
                raise HTTPException(status_code=422, detail="Expected ITM QR in item_qr_code")
            item_query = db.query(models.ProductItem).filter(models.ProductItem.uuid == parsed_item.uuid)
            item_query = self._with_row_lock(item_query)
            target_item = item_query.first()
            if not target_item:
                raise HTTPException(status_code=404, detail="Item for glass sale not found")
            self._assert_item_sellable(item=target_item, location_id=terminal.location_id)
            if target_item.product_id != product.id:
                raise HTTPException(status_code=422, detail="item_qr_code product does not match product_id")

        glasses_per_bottle = int(self.settings.glasses_per_bottle)
        if glasses_per_bottle <= 0:
            raise HTTPException(status_code=500, detail="Invalid glasses_per_bottle configuration")

        consumed_item_ids: list[int] = []
        remaining = glasses_requested
        if target_item is not None:
            consumed = self._consume_glasses_from_item(
                db=db,
                item=target_item,
                glasses=remaining,
                glasses_total=glasses_per_bottle,
            )
            if consumed < remaining:
                raise HTTPException(status_code=409, detail="Not enough remaining volume in selected item")
            consumed_item_ids.append(target_item.id)
            remaining = 0
        else:
            while remaining > 0:
                candidate = self._select_next_pour_candidate(
                    db=db,
                    location_id=terminal.location_id,
                    product_id=product.id,
                )
                if not candidate:
                    raise HTTPException(status_code=409, detail="Insufficient stock for glass sale")
                consumed = self._consume_glasses_from_item(
                    db=db,
                    item=candidate,
                    glasses=remaining,
                    glasses_total=glasses_per_bottle,
                )
                consumed_item_ids.append(candidate.id)
                remaining -= consumed

        ratio_per_glass = Decimal("1") / Decimal(glasses_per_bottle)
        stock_service.adjust_stock(
            location_id=terminal.location_id,
            product_id=product.id,
            quantity=-(ratio_per_glass * Decimal(glasses_requested)),
            unit_id=product.base_unit_id,
        )

        unit_id, unit_ratio = self._resolve_glass_unit(
            db=db,
            product=product,
            requested_unit_id=line.unit_id,
            ratio_per_glass=ratio_per_glass,
        )
        unit = self._get_unit(db, unit_id)
        unit_price = self._resolve_unit_price(
            db=db,
            location_id=terminal.location_id,
            product=product,
            unit_id=unit_id,
            ratio_to_base=unit_ratio,
        )
        quantity = Decimal(glasses_requested)
        total_price = (unit_price * quantity).quantize(Decimal("0.01"))
        return _ResolvedLine(
            kind="glass",
            product=product,
            quantity=quantity,
            unit_id=unit.id,
            unit_code=unit.code,
            unit_price=unit_price,
            total_price=total_price,
            resolved_item_ids=sorted(set(consumed_item_ids)),
        )

    def _build_register_payload(
        self,
        *,
        sale_id: int,
        terminal_id: str,
        user_id: int | None,
        sold_at: datetime,
        lines: list[_ResolvedLine],
    ) -> dict:
        sale_items = []
        for line in lines:
            sale_items.append(
                {
                    "product_id": line.product.sku or str(line.product.id),
                    "quantity": float(line.quantity),
                    "price": float(line.unit_price),
                }
            )

        return {
            "sales": [
                {
                    "sale_id": sale_id,
                    "terminal_id": terminal_id,
                    "user_id": user_id,
                    "timestamp": sold_at.isoformat().replace("+00:00", "Z"),
                    "items": sale_items,
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def _send_register_transactions_request(self, *, db: Session, terminal: models.Terminal, payload: dict) -> dict:
        method = "POST"
        path = "/api/v1/sales/register-sales-transactions"
        timestamp = str(int(time.time()))
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        signature = _generate_hmac_signature(method=method, path=path, body=body, secret=terminal.secret_hash, timestamp=timestamp)

        base_candidates: list[str] = [
            self.settings.sales_self_base_url,
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://backend_full:8000",
        ]
        bases: list[str] = []
        for candidate in base_candidates:
            value = (candidate or "").strip().rstrip("/")
            if value and value not in bases:
                bases.append(value)

        last_error_reason = ""
        for base in bases:
            url = f"{base}{path}"
            request_obj = urllib_request.Request(
                url=url,
                method=method,
                data=body.encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Terminal-ID": terminal.terminal_id,
                    "X-Signature": signature,
                    "X-Timestamp": timestamp,
                },
            )
            try:
                with urllib_request.urlopen(request_obj, timeout=self.settings.sales_self_timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib_error.HTTPError as exc:
                details = exc.read().decode("utf-8")
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to register sales transaction: HTTP {exc.code} {details}",
                ) from exc
            except urllib_error.URLError as exc:
                last_error_reason = str(exc.reason)
                continue

        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach sales API: {last_error_reason}. Tried: {', '.join(bases)}",
        )

    def _resolve_checkout_user_id(self, request_user_id: int | None) -> int | None:
        if self.settings.sales_terminal_user_id is not None:
            return int(self.settings.sales_terminal_user_id)
        return request_user_id

    def _select_sellable_items_fifo(
        self,
        *,
        db: Session,
        location_id: int,
        product_id: int,
        limit: int,
    ) -> list[models.ProductItem]:
        query_builder = (
            db.query(models.ProductItem)
            .join(models.StockLot, models.StockLot.id == models.ProductItem.lot_id)
            .join(models.Receipt, models.Receipt.id == models.StockLot.receipt_id)
            .outerjoin(models.ProductItemPour, models.ProductItemPour.product_item_id == models.ProductItem.id)
            .filter(
                models.ProductItem.location_id == location_id,
                models.ProductItem.product_id == product_id,
                models.ProductItem.status == "in_stock",
                models.ProductItem.reserved_transfer_doc_id.is_(None),
                models.Receipt.status != "void",
                or_(
                    models.ProductItemPour.product_item_id.is_(None),
                    models.ProductItemPour.glasses_sold == 0,
                ),
            )
            .order_by(models.StockLot.received_at.asc(), models.ProductItem.created_at.asc(), models.ProductItem.id.asc())
            .limit(limit)
        )
        query_builder = self._with_row_lock(query_builder, skip_locked=True, of_model=models.ProductItem)
        return query_builder.all()

    def _select_next_pour_candidate(self, *, db: Session, location_id: int, product_id: int) -> models.ProductItem | None:
        query_builder = (
            db.query(models.ProductItem)
            .join(models.StockLot, models.StockLot.id == models.ProductItem.lot_id)
            .join(models.Receipt, models.Receipt.id == models.StockLot.receipt_id)
            .filter(
                models.ProductItem.location_id == location_id,
                models.ProductItem.product_id == product_id,
                models.ProductItem.status == "in_stock",
                models.ProductItem.reserved_transfer_doc_id.is_(None),
                models.Receipt.status != "void",
            )
            .order_by(models.StockLot.received_at.asc(), models.ProductItem.created_at.asc(), models.ProductItem.id.asc())
            .limit(1)
        )
        query_builder = self._with_row_lock(query_builder, skip_locked=True)
        return query_builder.first()

    def _count_sellable_items(self, *, db: Session, location_id: int, product_id: int) -> int:
        return (
            db.query(models.ProductItem.id)
            .join(models.StockLot, models.StockLot.id == models.ProductItem.lot_id)
            .join(models.Receipt, models.Receipt.id == models.StockLot.receipt_id)
            .outerjoin(models.ProductItemPour, models.ProductItemPour.product_item_id == models.ProductItem.id)
            .filter(
                models.ProductItem.location_id == location_id,
                models.ProductItem.product_id == product_id,
                models.ProductItem.status == "in_stock",
                models.ProductItem.reserved_transfer_doc_id.is_(None),
                models.Receipt.status != "void",
                or_(
                    models.ProductItemPour.product_item_id.is_(None),
                    models.ProductItemPour.glasses_sold == 0,
                ),
            )
            .count()
        )

    def _consume_glasses_from_item(
        self,
        *,
        db: Session,
        item: models.ProductItem,
        glasses: int,
        glasses_total: int,
    ) -> int:
        if item.box_id is not None:
            box = item.box
            if box and box.sealed:
                box.sealed = False
            self._detach_item_from_box(item)

        pour = (
            db.query(models.ProductItemPour)
            .filter(models.ProductItemPour.product_item_id == item.id)
            .first()
        )
        if not pour:
            pour = models.ProductItemPour(
                product_item_id=item.id,
                glasses_total=glasses_total,
                glasses_sold=0,
            )
            db.add(pour)
            db.flush()

        remaining = pour.glasses_total - pour.glasses_sold
        if remaining <= 0:
            return 0

        consumed = min(remaining, glasses)
        pour.glasses_sold += consumed
        if pour.glasses_sold >= pour.glasses_total:
            self._sell_item(None, item.location_id, item, adjust_stock=False)
        return consumed

    def _sell_item(
        self,
        serial_stock: SerialStockLedger | None,
        location_id: int,
        item: models.ProductItem,
        *,
        adjust_stock: bool,
    ) -> None:
        self._assert_item_sellable(item=item, location_id=location_id)
        if item.box_id is not None:
            self._detach_item_from_box(item)
        item.status = "sold"
        item.reserved_transfer_doc_id = None
        item.reserved_at = None
        if adjust_stock:
            if serial_stock is None:
                raise HTTPException(status_code=500, detail="Internal error: missing stock ledger")
            serial_stock.adjust_base_units(location_id=location_id, product_id=item.product_id, delta_base_units=-1)

    def _detach_item_from_box(self, item: models.ProductItem) -> None:
        if item.box_id is None:
            return
        box = item.box
        if box and box.quantity > 0:
            box.quantity -= 1
        item.box_id = None

    @staticmethod
    def _assert_item_sellable(*, item: models.ProductItem, location_id: int) -> None:
        if item.status != "in_stock":
            raise HTTPException(status_code=409, detail="Item is not available for sale")
        if item.location_id != location_id:
            raise HTTPException(status_code=409, detail="Item is in another location")
        if item.reserved_transfer_doc_id is not None:
            raise HTTPException(status_code=409, detail="Item is reserved for transfer")

    @staticmethod
    def _positive_decimal(value: Decimal | None, *, field_name: str) -> Decimal:
        if value is None:
            raise HTTPException(status_code=422, detail=f"{field_name} is required")
        quantity = Decimal(str(value))
        if quantity <= 0:
            raise HTTPException(status_code=422, detail=f"{field_name} must be positive")
        return quantity

    @staticmethod
    def _positive_integer_quantity(value: Decimal | None, *, field_name: str) -> int:
        quantity = SalesCheckoutHandler._positive_decimal(value, field_name=field_name)
        quantity_int = int(quantity.to_integral_value(rounding=ROUND_DOWN))
        if Decimal(quantity_int) != quantity:
            raise HTTPException(status_code=422, detail=f"{field_name} must be an integer")
        return quantity_int

    @staticmethod
    def _to_int_base_units(value: Decimal) -> int:
        integer = int(value.to_integral_value(rounding=ROUND_DOWN))
        if Decimal(integer) != value:
            raise HTTPException(status_code=422, detail="Quantity must map to whole serialized items")
        if integer <= 0:
            raise HTTPException(status_code=422, detail="Quantity must be positive")
        return integer

    @staticmethod
    def _with_row_lock(query_builder, *, skip_locked: bool = False, of_model=None):
        session = getattr(query_builder, "session", None)
        bind = getattr(session, "bind", None)
        if bind and bind.dialect.name == "postgresql":
            if of_model is not None:
                return query_builder.with_for_update(of=of_model, skip_locked=skip_locked)
            return query_builder.with_for_update(skip_locked=skip_locked)
        return query_builder

    @staticmethod
    def _get_product(db: Session, product_id: int) -> models.Product:
        product = db.query(models.Product).get(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @staticmethod
    def _get_unit(db: Session, unit_id: int) -> models.Unit:
        unit = db.query(models.Unit).get(unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")
        return unit

    def _ratio_to_base(self, db: Session, product: models.Product, unit_id: int) -> Decimal:
        if unit_id == product.base_unit_id:
            return Decimal("1")
        row = (
            db.query(models.ProductUnit.ratio_to_base)
            .filter(
                models.ProductUnit.product_id == product.id,
                models.ProductUnit.unit_id == unit_id,
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=422, detail="Missing product unit conversion")
        return Decimal(str(row[0]))

    def _resolve_glass_unit(
        self,
        *,
        db: Session,
        product: models.Product,
        requested_unit_id: int | None,
        ratio_per_glass: Decimal,
    ) -> tuple[int, Decimal]:
        if requested_unit_id is not None:
            if requested_unit_id == product.base_unit_id:
                return requested_unit_id, ratio_per_glass
            try:
                return requested_unit_id, self._ratio_to_base(db, product, requested_unit_id)
            except HTTPException:
                return requested_unit_id, ratio_per_glass

        glass_unit = (
            db.query(models.ProductUnit.unit_id, models.ProductUnit.ratio_to_base)
            .join(models.Unit, models.Unit.id == models.ProductUnit.unit_id)
            .filter(
                models.ProductUnit.product_id == product.id,
                models.Unit.unit_type == "portion",
            )
            .order_by(models.ProductUnit.ratio_to_base.asc(), models.ProductUnit.unit_id.asc())
            .first()
        )
        if glass_unit:
            return int(glass_unit[0]), Decimal(str(glass_unit[1]))
        return product.base_unit_id, ratio_per_glass

    @staticmethod
    def _is_serial_product(db: Session, product: models.Product) -> bool:
        unit = db.query(models.Unit).get(product.base_unit_id)
        return bool(unit and unit.is_discrete)

    def _resolve_unit_price(
        self,
        *,
        db: Session,
        location_id: int,
        product: models.Product,
        unit_id: int,
        ratio_to_base: Decimal,
    ) -> Decimal:
        price_row = (
            db.query(models.PriceList.amount)
            .filter(
                models.PriceList.location_id == location_id,
                models.PriceList.product_id == product.id,
                models.PriceList.unit_id == unit_id,
            )
            .first()
        )
        if price_row:
            return Decimal(str(price_row[0])).quantize(Decimal("0.01"))

        base_cost = Decimal(str(product.base_cost or 0))
        if base_cost <= 0:
            return Decimal("0.00")
        return (base_cost * ratio_to_base).quantize(Decimal("0.01"))

    def _find_package_unit_by_size(self, db: Session, product_id: int, box_quantity: int) -> models.ProductUnit | None:
        if box_quantity <= 0:
            return None
        return (
            db.query(models.ProductUnit)
            .join(models.Unit, models.Unit.id == models.ProductUnit.unit_id)
            .filter(
                models.ProductUnit.product_id == product_id,
                models.Unit.unit_type == "package",
                models.ProductUnit.ratio_to_base == Decimal(box_quantity),
            )
            .first()
        )


class SellProductHandler:
    """
    Backward-compatible endpoint wrapper.

    Uses the new checkout flow with a single `product` line.
    """

    def handle(self, command: SellProductCommand, uow: AbstractUnitOfWork) -> dict:
        payload = schemas.SaleCheckoutRequest(
            lines=[
                schemas.SaleCheckoutLineIn(
                    kind="product",
                    product_id=command.payload.product_id,
                    quantity=command.payload.quantity,
                )
            ]
        )
        result = SalesCheckoutHandler().handle(SaleCheckoutCommand(payload=payload), uow)
        line = result.lines[0] if result.lines else None
        product_name = line.product_name if line else str(command.payload.product_id)
        return {
            "message": f"Successfully sold {command.payload.quantity} of {product_name}",
            "total_cost": str(result.total_amount),
        }


class SellWineGlassHandler:
    """
    Backward-compatible endpoint wrapper.

    Uses the new checkout flow with a single `glass` line.
    """

    def handle(self, command: SellWineGlassCommand, uow: AbstractUnitOfWork) -> dict:
        payload = schemas.SaleCheckoutRequest(
            lines=[
                schemas.SaleCheckoutLineIn(
                    kind="glass",
                    product_id=command.payload.product_id,
                    quantity=command.payload.quantity,
                )
            ]
        )
        result = SalesCheckoutHandler().handle(SaleCheckoutCommand(payload=payload), uow)
        line = result.lines[0] if result.lines else None
        product_name = line.product_name if line else str(command.payload.product_id)
        return {
            "message": f"Successfully sold {command.payload.quantity} glasses of {product_name}",
            "total_cost": str(result.total_amount),
        }
