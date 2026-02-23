from __future__ import annotations

import structlog

from app.domain.event_bus import subscribe
from app.domain.events import ProductSoldEvent


logger = structlog.get_logger()


@subscribe(ProductSoldEvent)
def on_product_sold(event: ProductSoldEvent) -> None:
    logger.info(
        "domain_event.product_sold",
        sale_id=event.sale_id,
        product_id=event.product_id,
        quantity=str(event.quantity),
        unit_id=event.unit_id,
        occurred_at=event.occurred_at.isoformat(),
    )
