from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.pricing_calculators.base import BasePriceCalculator


class ExampleMultiplierCalculatorV2(BasePriceCalculator):
    """Example v2: amount * multiplier + offset + floor."""

    calculator_code = "example_multiplier"
    calculator_name = "Example Multiplier"
    calculator_version = "1.1.0"
    description = "amount * multiplier + offset + floor"
    changelog = "Added optional floor guard"

    def calculate(
        self,
        *,
        current_amount: Decimal,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> Decimal:
        multiplier = Decimal(str(params.get("multiplier", "1")))
        offset = Decimal(str(params.get("offset", "0")))
        floor = Decimal(str(params.get("floor", "0")))
        amount = (current_amount * multiplier) + offset
        return amount if amount >= floor else floor
