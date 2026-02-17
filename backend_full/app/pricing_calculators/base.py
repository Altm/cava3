from __future__ import annotations

from decimal import Decimal
from typing import Any


class BasePriceCalculator:
    """Base contract for file-based price calculators."""

    calculator_code: str = "base_calculator"
    calculator_name: str = "Base Calculator"
    calculator_version: str = "1.0.0"
    description: str = "Custom calculator"
    changelog: str | None = None

    def calculate(
        self,
        *,
        current_amount: Decimal,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> Decimal:
        raise NotImplementedError
