from __future__ import annotations

from decimal import Decimal
from typing import Any


class BasePriceCalculator:
    """Base contract for file-based price calculators."""

    description: str = "Custom calculator"

    def calculate(
        self,
        *,
        current_amount: Decimal,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> Decimal:
        raise NotImplementedError

