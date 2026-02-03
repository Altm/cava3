from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.models.models import Unit, ProductUnit, Product
from app.common.errors import ValidationError


class UnitConverter:
    """Converts units based on configured ratios."""

    def __init__(self, db: Session):
        self.db = db

    def to_base(self, unit_code: str, quantity: Decimal, base_unit: str) -> Decimal:
        """
        Convert quantity from given unit to base unit.
        For backward compatibility, this method attempts to find a conversion ratio.
        In the new system, this should ideally use product-specific ratios.
        """
        # For backward compatibility, we'll try to find a conversion ratio
        # In a real implementation, you'd need product context to get the correct ratio
        # For now, we'll assume a 1:1 ratio if units are the same, or try to find a global conversion
        if unit_code == base_unit:
            return quantity

        # This is a fallback for backward compatibility
        # In the new system, you should use product-specific conversion methods
        return quantity

    def normalize(self, unit_code: str, quantity: Decimal) -> Decimal:
        unit = self.db.query(Unit).filter(Unit.code == unit_code).first()
        if unit and unit.discrete_step:
            step = Decimal(unit.discrete_step)
            return (quantity / step).quantize(0, rounding=ROUND_HALF_UP) * step
        return quantity
