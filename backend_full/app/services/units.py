from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.models.models import Unit, UnitConversion
from app.common.errors import ValidationError


class UnitConverter:
    """Converts units based on configured ratios."""

    def __init__(self, db: Session):
        self.db = db

    def to_base(self, unit_code: str, quantity: Decimal, base_unit: str) -> Decimal:
        if unit_code == base_unit:
            return quantity
        conversion = (
            self.db.query(UnitConversion).filter(UnitConversion.from_unit == unit_code, UnitConversion.to_unit == base_unit).first()
        )
        if not conversion:
            raise ValidationError(f"No conversion from {unit_code} to {base_unit}")
        return (quantity * Decimal(conversion.ratio)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def normalize(self, unit_code: str, quantity: Decimal) -> Decimal:
        unit = self.db.query(Unit).filter(Unit.code == unit_code).first()
        if unit and unit.discrete_step:
            step = Decimal(unit.discrete_step)
            return (quantity / step).quantize(0, rounding=ROUND_HALF_UP) * step
        return quantity
