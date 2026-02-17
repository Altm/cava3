from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.pricing_calculators.base import BasePriceCalculator


class ExampleMultiplierCalculator(BasePriceCalculator):
    """Example: amount * multiplier + offset."""

    description = "amount * multiplier + offset"

    def calculate(
        self,
        *,
        current_amount: Decimal,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> Decimal:
        multiplier = Decimal(str(params.get("multiplier", "1")))
        offset = Decimal(str(params.get("offset", "0")))
        return (current_amount * multiplier) + offset

