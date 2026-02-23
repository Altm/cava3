from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol


class DomainEvent(Protocol):
    occurred_at: datetime


@dataclass(frozen=True)
class ProductSoldEvent:
    sale_id: int
    product_id: int
    quantity: Decimal
    unit_id: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
