from datetime import datetime
from decimal import Decimal
from typing import List
from sqlalchemy.orm import Session
from app.common.errors import IdempotencyError
from app.models.models import SaleEvent, SaleLine, Product, CompositeComponent
from app.services.stock_service import StockService
import structlog

logger = structlog.get_logger()


class SalesService:
    """Handles ingestion and reconciliation of sale events."""

    def __init__(self, db: Session):
        self.db = db
        self.stock_service = StockService(db)

    def ingest_sale(self, event_id: str, terminal_id: int, location_id: int, lines: List[dict]) -> SaleEvent:
        existing = self.db.query(SaleEvent).filter_by(event_id=event_id).first()
        if existing:
            raise IdempotencyError("Event already ingested")
        payload = {"lines": lines}
        sale = SaleEvent(event_id=event_id, terminal_id=terminal_id, location_id=location_id, payload=payload, status="pending")
        self.db.add(sale)
        self.db.flush()
        for line in lines:
            sale_line = SaleLine(
                sale_event_id=sale.id,
                product_id=line["product_id"],
                quantity=Decimal(str(line["quantity"])),
                unit_code=line["unit"],
                currency=line.get("currency", "USD"),
                price=Decimal(str(line.get("price", "0"))),
            )
            self.db.add(sale_line)
        logger.info("sale_ingested", event_id=event_id)
        return sale

    def _expand_components(self, product_id: int, quantity: Decimal, unit: str) -> List[dict]:
        components = self.db.query(CompositeComponent).filter_by(parent_product_id=product_id).all()
        if not components:
            return [{"product_id": product_id, "quantity": quantity, "unit": unit}]
        expanded: List[dict] = []
        for comp in components:
            expanded.append(
                {
                    "product_id": comp.component_product_id,
                    "quantity": quantity * Decimal(comp.quantity),
                    "unit": comp.unit_code,
                }
            )
        return expanded

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
                expanded = self._expand_components(line["product_id"], Decimal(str(line["quantity"])), line["unit"])
                for comp_line in expanded:
                    pid = comp_line["product_id"]
                    delta_counter.setdefault(pid, {"qty": Decimal("0"), "unit": comp_line["unit"]})
                    delta_counter[pid]["qty"] += Decimal(str(comp_line["quantity"]))
        for product_id, info in delta_counter.items():
            self.stock_service.adjust_stock(location_id, product_id, -info["qty"], info["unit"])
        self.db.query(SaleEvent).filter(SaleEvent.event_id.in_(applied_events)).update(
            {"status": "confirmed", "confirmed_at": datetime.utcnow()}, synchronize_session=False
        )
        logger.info("daily_reconcile", terminal_id=terminal_id, location_id=location_id, events=len(applied_events))
        return {"confirmed_events": applied_events, "applied_products": list(delta_counter.keys())}
