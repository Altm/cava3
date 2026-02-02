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
        NOTE: With the new product-specific unit system, this method may not work as expected
        without product context. Consider using product-specific methods.
        For backward compatibility, this method raises an error indicating the change.
        """
        # The old unit conversion system has been replaced with product-specific conversions
        # The unit_conversion table was removed and replaced with product_unit table
        raise ValidationError(
            f"Unit conversion logic has been updated to be product-specific. "
            f"Use product-specific conversion methods instead. "
            f"Conversion from {unit_code} to {base_unit} requires product context."
        )

    def normalize(self, unit_code: str, quantity: Decimal) -> Decimal:
        unit = self.db.query(Unit).filter(Unit.code == unit_code).first()
        if unit and unit.discrete_step:
            step = Decimal(unit.discrete_step)
            return (quantity / step).quantize(0, rounding=ROUND_HALF_UP) * step
        return quantity
