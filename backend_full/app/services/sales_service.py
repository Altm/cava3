import json
from datetime import datetime
from decimal import Decimal
from hashlib import sha1
from typing import List
from sqlalchemy.orm import Session
from app.common.errors import IdempotencyError
from app.domain.composite import CompositeCycleError, CompositeDecompositionService
from app.models.models import Product, SaleEvent, SaleLine, Terminal, Unit
from app.services.stock_service import StockService
import structlog

logger = structlog.get_logger()


class SalesService:
    """Handles ingestion and reconciliation of sale events."""

    def __init__(self, db: Session):
        self.db = db
        self.stock_service = StockService(db)

    def _convert_decimal_in_payload(self, obj):
        """Convert Decimal objects to float for JSON serialization"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, list):
            return [self._convert_decimal_in_payload(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimal_in_payload(value) for key, value in obj.items()}
        return obj

    def ingest_sale(
        self,
        event_id: str,
        terminal_id: int,
        location_id: int,
        lines: List[dict],
        *,
        sale_id: int | None = None,
        user_id: int | None = None,
        status: str = "pending",
        payload: dict | None = None,
    ) -> SaleEvent:
        existing = self.db.query(SaleEvent).filter_by(event_id=event_id).first()
        if existing:
            raise IdempotencyError("Event already ingested")

        if payload is None:
            serialized_lines = self._convert_decimal_in_payload(lines)
            payload = {"lines": serialized_lines}

        confirmed_at = datetime.utcnow() if status == "confirmed" else None
        sale = SaleEvent(
            event_id=event_id,
            sale_id=sale_id,
            user_id=user_id,
            terminal_id=terminal_id,
            location_id=location_id,
            payload=payload,
            status=status,
            confirmed_at=confirmed_at,
        )
        self.db.add(sale)
        self.db.flush()
        for line in lines:
            unit = self.db.query(Unit).filter(Unit.code == line["unit"]).first()
            if not unit:
                raise ValueError(f"Unknown unit code: {line['unit']}")
            sale_line = SaleLine(
                sale_event_id=sale.id,
                product_id=line["product_id"],
                quantity=Decimal(str(line["quantity"])),
                unit_id=unit.id,
                currency=line.get("currency", "USD"),
                price=Decimal(str(line.get("price", "0"))),
            )
            self.db.add(sale_line)
        logger.info("sale_ingested", event_id=event_id)
        return sale

    def register_sales_transactions(self, terminal: Terminal, payload: dict, default_status: str) -> dict:
        """
        Регистрирует пакет sales transactions с идемпотентностью.
        
        Идемпотентность обеспечивается на двух уровнях:
        1. По event_id (идентификатор события продажи)
        2. По хешу позиции (product_id + quantity + unit_id + timestamp)
        
        Одинаковые позиции не дублируются, даже если отправлены повторно.
        """
        sales = payload.get("sales")
        if not isinstance(sales, list):
            raise ValueError("Field 'sales' must be a list")

        normalized_status = self._normalize_status(default_status)
        created_event_ids: list[str] = []
        skipped_event_ids: list[str] = []
        duplicate_positions: list[str] = []

        for sale_payload in sales:
            if not isinstance(sale_payload, dict):
                continue
            
            # Level 1: Идемпотентность по event_id
            event_id = self._build_event_id(terminal.terminal_id, sale_payload)
            existing_event = self.db.query(SaleEvent).filter(SaleEvent.event_id == event_id).first()
            if existing_event:
                skipped_event_ids.append(event_id)
                continue

            sale_id = self._to_int(sale_payload.get("sale_id"))
            user_id = self._to_int(sale_payload.get("user_id"))
            item_rows = sale_payload.get("items")
            if not isinstance(item_rows, list):
                item_rows = []

            # Level 2: Идемпотентность на уровне позиций
            # Фильтруем дубликаты позиций внутри одной продажи
            seen_positions = set()
            unique_lines: list[dict] = []
            
            for row in item_rows:
                if not isinstance(row, dict):
                    continue
                
                product = self._resolve_product(row.get("product_id"))
                quantity = Decimal(str(row.get("quantity", "0")))
                if quantity <= 0:
                    continue
                    
                # Создаём уникальный хеш для позиции
                position_key = self._build_position_hash(
                    terminal_id=terminal.terminal_id,
                    sale_id=sale_id,
                    product_id=product.id,
                    quantity=quantity,
                    timestamp=sale_payload.get("timestamp", ""),
                )
                
                # Проверяем, не была ли уже зарегистрирована такая позиция
                if position_key in seen_positions:
                    duplicate_positions.append(position_key)
                    continue  # Пропускаем дубликат
                
                seen_positions.add(position_key)
                
                price = Decimal(str(row.get("price", "0")))
                unique_lines.append(
                    {
                        "product_id": product.id,
                        "quantity": quantity,
                        "unit": self._resolve_unit_code(product.base_unit_id),
                        "price": price * quantity,
                        "position_hash": position_key,  # Сохраняем хеш для аудита
                    }
                )

            # Если все позиции были дубликатами, пропускаем всю продажу
            if not unique_lines:
                skipped_event_ids.append(event_id)
                continue

            event_payload = {
                "sale": self._convert_decimal_in_payload(sale_payload),
                "batch_timestamp": payload.get("timestamp"),
            }
            sale = self.ingest_sale(
                event_id=event_id,
                sale_id=sale_id,
                user_id=user_id,
                terminal_id=terminal.id,
                location_id=terminal.location_id,
                lines=unique_lines,
                status=normalized_status,
                payload=event_payload,
            )
            created_event_ids.append(sale.event_id)

        logger.info(
            "sales_transactions_registered",
            terminal_id=terminal.terminal_id,
            created=len(created_event_ids),
            skipped=len(skipped_event_ids),
            duplicates=len(duplicate_positions),
        )
        return {
            "status": "success",
            "created_event_ids": created_event_ids,
            "skipped_event_ids": skipped_event_ids,
            "duplicate_positions": duplicate_positions,
            "received_sales_count": len(sales),
            "processed_positions_count": len(unique_lines) if 'unique_lines' in locals() else 0,
        }

    @staticmethod
    def _build_position_hash(
        terminal_id: str,
        sale_id: int | None,
        product_id: int,
        quantity: Decimal,
        timestamp: str,
    ) -> str:
        """
        Создаёт уникальный хеш для позиции продажи.
        
        Используется для предотвращения дублирования одинаковых позиций
        при повторной отправке данных за тот же период.
        """
        import hashlib
        position_data = f"{terminal_id}:{sale_id}:{product_id}:{quantity}:{timestamp}"
        return hashlib.sha256(position_data.encode()).hexdigest()[:32]

    def _resolve_product(self, product_ref) -> Product:
        if product_ref is None:
            raise ValueError("product_id is required")
        parsed_id = self._to_int(product_ref)
        product = self.db.get(Product, parsed_id) if parsed_id is not None else None
        if product:
            return product
        product_by_sku = self.db.query(Product).filter(Product.sku == str(product_ref)).first()
        if not product_by_sku:
            raise ValueError(f"Unknown product reference: {product_ref}")
        return product_by_sku

    def _resolve_unit_code(self, unit_id: int) -> str:
        unit = self.db.get(Unit, unit_id)
        if not unit:
            raise ValueError(f"Unknown unit_id: {unit_id}")
        return unit.code

    @staticmethod
    def _normalize_status(status: str) -> str:
        value = (status or "").strip().lower()
        if value in {"pending", "confirmed"}:
            return value
        return "pending"

    @staticmethod
    def _build_event_id(terminal_public_id: str, sale_payload: dict) -> str:
        explicit = sale_payload.get("event_id")
        if explicit:
            return str(explicit)[:128]
        sale_id = SalesService._to_int(sale_payload.get("sale_id"))
        if sale_id is not None:
            return f"register:{terminal_public_id}:{sale_id}"
        serialized = json.dumps(sale_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = sha1(serialized.encode("utf-8")).hexdigest()[:20]
        return f"register:{terminal_public_id}:{digest}"

    @staticmethod
    def _to_int(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _expand_components(self, product_id: int, quantity: Decimal, unit_id: int, location_id: int | None = None) -> List[dict]:
        product = self.db.get(Product, product_id)
        if not product:
            return []
        ratio_to_base = Decimal("1")
        if unit_id != product.base_unit_id:
            ratio_to_base = self.stock_service._to_base(product.id, unit_id, Decimal("1"))  # noqa: SLF001

        qty_base = Decimal(quantity) * Decimal(str(ratio_to_base))
        if not (product.product_type and product.product_type.is_composite):
            return [
                {
                    "product_id": product.id,
                    "quantity": qty_base,
                    "unit_id": product.base_unit_id,
                }
            ]

        decomposition = CompositeDecompositionService(self.db)
        try:
            requirements = decomposition.decompose(
                product_id=product_id,
                quantity_base=qty_base,
                location_id=location_id,
            )
        except CompositeCycleError:
            return []
        result: list[dict] = []
        for req in requirements:
            leaf = self.db.get(Product, req.product_id)
            if not leaf:
                continue
            result.append(
                {
                    "product_id": req.product_id,
                    "quantity": req.quantity_base,
                    "unit_id": leaf.base_unit_id,
                }
            )
        return result

    def reconcile_daily(self, terminal_id: int, location_id: int, events: List[dict]) -> dict:
        applied_events = []
        delta_counter: dict[int, dict[str, Decimal]] = {}
        for event in events:
            event_id = event["event_id"]
            lines = event["lines"]
            existing = self.db.query(SaleEvent).filter_by(event_id=event_id).first()
            if existing and existing.status == "confirmed":
                continue
            if not existing:
                self.ingest_sale(event_id, terminal_id, location_id, lines)
            applied_events.append(event_id)
            for line in lines:
                unit = self.db.query(Unit).filter(Unit.code == line["unit"]).first()
                if not unit:
                    raise ValueError(f"Unknown unit code: {line['unit']}")
                expanded = self._expand_components(
                    line["product_id"],
                    Decimal(str(line["quantity"])),
                    unit.id,
                    location_id=location_id,
                )
                for comp_line in expanded:
                    pid = comp_line["product_id"]
                    delta_counter.setdefault(pid, {"qty": Decimal("0"), "unit_id": comp_line["unit_id"]})
                    delta_counter[pid]["qty"] += Decimal(str(comp_line["quantity"]))
        for product_id, info in delta_counter.items():
            self.stock_service.adjust_stock(location_id, product_id, -info["qty"], info["unit_id"])
        self.db.query(SaleEvent).filter(SaleEvent.event_id.in_(applied_events)).update(
            {"status": "confirmed", "confirmed_at": datetime.utcnow()}, synchronize_session=False
        )
        logger.info("daily_reconcile", terminal_id=terminal_id, location_id=location_id, events=len(applied_events))
        return {"confirmed_events": applied_events, "applied_products": list(delta_counter.keys())}
