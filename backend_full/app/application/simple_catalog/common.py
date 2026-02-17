from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import models
from app.models.models import ProductMeta
from app.schemas import simple as schemas


def default_location(db: Session) -> models.Location:
    settings = get_settings()
    loc = db.query(models.Location).filter(models.Location.id == settings.default_location_id).first()
    if loc:
        return loc

    loc = db.query(models.Location).filter(models.Location.name == settings.default_location_name).first()
    if loc:
        return loc

    loc = db.query(models.Location).first()
    if not loc:
        loc = models.Location(name=settings.default_location_name, code="warehouse")
        db.add(loc)
        db.flush()
    return loc


class ProductAvailabilityCalculator:
    def __init__(self, db: Session, location_id: Optional[int] = None):
        self.db = db
        self.location_id = location_id
        self._product_cache: dict[int, models.Product] = {}
        self._component_cache: dict[int, list[models.ProductComposite]] = {}
        self._ratio_cache: dict[tuple[int, int], Optional[Decimal]] = {}
        self._stock_base_cache: dict[int, Decimal] = {}
        self._available_cache: dict[int, Decimal] = {}
        self._unit_discrete_cache: dict[int, bool] = {}
        self._unit_cache: dict[int, models.Unit] = {}

    def unit(self, unit_id: int) -> Optional[models.Unit]:
        cached = self._unit_cache.get(unit_id)
        if cached is not None:
            return cached
        unit = self.db.query(models.Unit).get(unit_id)
        if unit:
            self._unit_cache[unit_id] = unit
        return unit

    def product(self, product_id: int) -> Optional[models.Product]:
        cached = self._product_cache.get(product_id)
        if cached is not None:
            return cached
        product = self.db.query(models.Product).get(product_id)
        if product:
            self._product_cache[product_id] = product
        return product

    def components(self, product_id: int) -> list[models.ProductComposite]:
        cached = self._component_cache.get(product_id)
        if cached is not None:
            return cached
        rows = (
            self.db.query(models.ProductComposite)
            .filter(models.ProductComposite.parent_product_id == product_id)
            .order_by(models.ProductComposite.id.asc())
            .all()
        )
        self._component_cache[product_id] = rows
        return rows

    def _ratio_to_base(self, product: models.Product, unit_id: int) -> Optional[Decimal]:
        cache_key = (product.id, unit_id)
        if cache_key in self._ratio_cache:
            return self._ratio_cache[cache_key]
        if unit_id == product.base_unit_id:
            ratio = Decimal("1")
        else:
            row = (
                self.db.query(models.ProductUnit.ratio_to_base)
                .filter(
                    models.ProductUnit.product_id == product.id,
                    models.ProductUnit.unit_id == unit_id,
                )
                .first()
            )
            ratio = Decimal(str(row[0])) if row else Decimal("1")
        self._ratio_cache[cache_key] = ratio
        return ratio

    def _sum_stock_base(self, product: models.Product) -> Decimal:
        cached = self._stock_base_cache.get(product.id)
        if cached is not None:
            return cached
        query_builder = self.db.query(models.Stock.quantity, models.Stock.unit_id).filter(models.Stock.product_id == product.id)
        if self.location_id is not None:
            query_builder = query_builder.filter(models.Stock.location_id == self.location_id)
        total_base = Decimal("0")
        for qty, unit_id in query_builder.all():
            qty_decimal = Decimal(str(qty or 0))
            ratio = self._ratio_to_base(product, unit_id)
            if ratio is None:
                continue
            total_base += qty_decimal * ratio
        self._stock_base_cache[product.id] = total_base
        return total_base

    def _base_unit_is_discrete(self, product: models.Product) -> bool:
        if product.id in self._unit_discrete_cache:
            return self._unit_discrete_cache[product.id]
        unit = self.unit(product.base_unit_id)
        value = bool(unit.is_discrete) if unit else False
        self._unit_discrete_cache[product.id] = value
        return value

    def available_quantity(self, product_id: int, stack: Optional[set[int]] = None) -> Decimal:
        if product_id in self._available_cache:
            return self._available_cache[product_id]
        product = self.product(product_id)
        if not product:
            return Decimal("0")

        own_stock_base = self._sum_stock_base(product)
        if not product.product_type or not product.product_type.is_composite:
            self._available_cache[product_id] = own_stock_base
            return own_stock_base

        components = self.components(product_id)
        if not components:
            self._available_cache[product_id] = own_stock_base
            return own_stock_base

        active_stack = stack or set()
        if product_id in active_stack:
            return Decimal("0")
        active_stack.add(product_id)
        try:
            min_bundles: Optional[Decimal] = None
            for comp in components:
                component_product = self.product(comp.component_product_id)
                if not component_product:
                    min_bundles = Decimal("0")
                    break
                required_qty = Decimal(str(comp.quantity or 0))
                if required_qty <= 0:
                    continue
                required_ratio = self._ratio_to_base(component_product, comp.unit_id)
                if required_ratio is None or required_ratio <= 0:
                    min_bundles = Decimal("0")
                    break
                required_base = required_qty * required_ratio
                component_available_base = self.available_quantity(component_product.id, active_stack)
                bundles = component_available_base / required_base
                if min_bundles is None or bundles < min_bundles:
                    min_bundles = bundles
            if min_bundles is None:
                min_bundles = Decimal("0")
            if self._base_unit_is_discrete(product):
                available = min_bundles.to_integral_value(rounding=ROUND_DOWN)
            else:
                available = min_bundles.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
            self._available_cache[product_id] = available
            return available
        finally:
            active_stack.remove(product_id)


def _serialize_product_units(db_product: models.Product) -> list[schemas.ProductUnit]:
    rows = sorted(
        db_product.product_units or [],
        key=lambda unit: (
            Decimal(str(unit.ratio_to_base or 0)),
            unit.unit_id,
        ),
        reverse=True,
    )
    return [
        schemas.ProductUnit(
            id=row.id,
            product_id=row.product_id,
            unit_id=row.unit_id,
            ratio_to_base=Decimal(str(row.ratio_to_base)),
            discrete_step=Decimal(str(row.discrete_step)) if row.discrete_step is not None else None,
        )
        for row in rows
    ]


def _build_display_quantity(
    base_quantity: Decimal,
    *,
    product_units: list[schemas.ProductUnit],
    unit_meta: dict[int, models.Unit],
    base_unit_id: int,
) -> str:
    if base_quantity <= 0:
        base_code = unit_meta.get(base_unit_id).code if unit_meta.get(base_unit_id) else str(base_unit_id)
        return f"0 {base_code}"

    remaining = base_quantity
    parts: list[str] = []
    ordered = sorted(product_units, key=lambda row: Decimal(str(row.ratio_to_base)), reverse=True)
    for row in ordered:
        unit = unit_meta.get(row.unit_id)
        if unit is None:
            continue
        ratio = Decimal(str(row.ratio_to_base))
        if ratio <= 0 or not unit.is_discrete:
            continue
        count = (remaining / ratio).to_integral_value(rounding=ROUND_DOWN)
        if count > 0:
            parts.append(f"{count} {unit.code}")
            remaining -= count * ratio

    remaining = remaining.quantize(Decimal("0.000001"))
    if remaining > 0:
        base_unit = unit_meta.get(base_unit_id)
        base_code = base_unit.code if base_unit else str(base_unit_id)
        parts.append(f"{remaining.normalize()} {base_code}")

    return " + ".join(parts) if parts else "0"


def _collect_product_tree_ids(calculator: ProductAvailabilityCalculator, product_id: int, seen: Optional[set[int]] = None) -> set[int]:
    visited = seen or set()
    if product_id in visited:
        return visited
    visited.add(product_id)
    for component in calculator.components(product_id):
        _collect_product_tree_ids(calculator, component.component_product_id, visited)
    return visited


def _build_stock_by_location(
    db_product: models.Product,
    db: Session,
    *,
    calculator: ProductAvailabilityCalculator,
    product_units: list[schemas.ProductUnit],
) -> list[schemas.ProductStockLocationView]:
    tree_product_ids = _collect_product_tree_ids(calculator, db_product.id)
    location_rows = (
        db.query(models.Location.id, models.Location.name, models.Location.code)
        .join(models.Stock, models.Stock.location_id == models.Location.id)
        .filter(models.Stock.product_id.in_(tree_product_ids))
        .distinct()
        .order_by(models.Location.id.asc())
        .all()
    )
    if not location_rows:
        return []

    unit_ids = {row.unit_id for row in product_units}
    if db_product.base_unit_id not in unit_ids:
        unit_ids.add(db_product.base_unit_id)
    unit_meta_rows = db.query(models.Unit).filter(models.Unit.id.in_(unit_ids)).all()
    unit_meta = {row.id: row for row in unit_meta_rows}

    result: list[schemas.ProductStockLocationView] = []
    for location_id, location_name, location_code in location_rows:
        location_calc = ProductAvailabilityCalculator(db, location_id=location_id)
        base_quantity = location_calc.available_quantity(db_product.id)
        unit_quantities = [
            schemas.ProductStockUnitQuantity(
                unit_id=row.unit_id,
                unit_code=unit_meta[row.unit_id].code if row.unit_id in unit_meta else str(row.unit_id),
                ratio_to_base=row.ratio_to_base,
                quantity=(base_quantity / Decimal(str(row.ratio_to_base))).quantize(Decimal("0.000001"))
                if Decimal(str(row.ratio_to_base)) > 0
                else Decimal("0"),
            )
            for row in product_units
        ]
        result.append(
            schemas.ProductStockLocationView(
                location_id=location_id,
                location_name=location_name,
                location_code=location_code,
                base_quantity=base_quantity,
                display_quantity=_build_display_quantity(
                    base_quantity,
                    product_units=product_units,
                    unit_meta=unit_meta,
                    base_unit_id=db_product.base_unit_id,
                ),
                units=unit_quantities,
            )
        )
    return result


def serialize_product(
    db_product: models.Product,
    db: Session,
    *,
    calculator: Optional[ProductAvailabilityCalculator] = None,
) -> schemas.Product:
    calc = calculator or ProductAvailabilityCalculator(db)
    attributes = []
    for attr in db_product.attributes:
        if attr.value_number is not None:
            val = attr.value_number
        elif attr.value_boolean is not None:
            val = attr.value_boolean
        elif attr.value_string is not None:
            val = attr.value_string
        else:
            val = None

        if val is not None:
            attributes.append(
                schemas.ProductAttributeValueCreate(
                    product_attribute_id=attr.product_attribute_id,
                    value=val,
                )
            )

    components = [
        schemas.ProductComponent(
            id=c.id,
            parent_product_id=c.parent_product_id,
            component_product_id=c.component_product_id,
            quantity=c.quantity,
            unit_id=c.unit_id,
            substitution_allowed=c.substitution_allowed,
            rounding=c.rounding,
        )
        for c in db_product.components
    ]
    product_units = _serialize_product_units(db_product)

    total_stock = calc.available_quantity(db_product.id)

    return schemas.Product(
        id=db_product.id,
        product_type_id=db_product.product_type_id,
        name=db_product.name,
        base_cost=db_product.base_cost or Decimal("0"),
        stock=total_stock,
        is_composite=db_product.product_type.is_composite,
        base_unit_id=db_product.base_unit_id,
        attributes=attributes,
        components=components,
        product_units=product_units,
    )


def _build_component_tree(
    parent_product_id: int,
    db: Session,
    *,
    calculator: ProductAvailabilityCalculator,
    path: Optional[set[int]] = None,
) -> list[schemas.ProductComponentTreeNode]:
    chain = path or set()
    rows = calculator.components(parent_product_id)
    result: list[schemas.ProductComponentTreeNode] = []
    for comp in rows:
        component_product = calculator.product(comp.component_product_id)
        if not component_product:
            continue
        unit = calculator.unit(comp.unit_id)
        is_cycle = component_product.id in chain
        children: list[schemas.ProductComponentTreeNode] = []
        if component_product.product_type and component_product.product_type.is_composite and not is_cycle:
            next_chain = set(chain)
            next_chain.add(component_product.id)
            children = _build_component_tree(
                component_product.id,
                db,
                calculator=calculator,
                path=next_chain,
            )
        result.append(
            schemas.ProductComponentTreeNode(
                component_product_id=component_product.id,
                component_name=component_product.name,
                quantity=Decimal(str(comp.quantity or 0)),
                unit_id=comp.unit_id,
                unit_code=unit.code if unit else None,
                is_composite=bool(component_product.product_type and component_product.product_type.is_composite),
                available_quantity=calculator.available_quantity(component_product.id),
                is_cycle=is_cycle,
                children=children,
            )
        )
    return result


def serialize_product_view(
    db_product: models.Product,
    db: Session,
    *,
    calculator: Optional[ProductAvailabilityCalculator] = None,
) -> schemas.ProductView:
    calc = calculator or ProductAvailabilityCalculator(db)
    base = serialize_product(db_product, db, calculator=calc)
    product_units = base.product_units or []
    meta = db.query(ProductMeta).filter(ProductMeta.product_id == db_product.id).first()
    meta_out = None
    if meta:
        meta_out = schemas.ProductMetaView(
            image=meta.image,
            body_html=meta.body_html,
            vendor=meta.vendor,
            type=meta.type,
            tags=meta.tags,
            variant_barcode=meta.variant_barcode,
            seo_title=meta.seo_title,
            seo_description=meta.seo_description,
        )
    component_tree = _build_component_tree(
        db_product.id,
        db,
        calculator=calc,
        path={db_product.id},
    )
    stock_by_location = _build_stock_by_location(
        db_product,
        db,
        calculator=calc,
        product_units=product_units,
    )
    return schemas.ProductView(
        **base.model_dump(),
        meta=meta_out,
        component_tree=component_tree,
        stock_by_location=stock_by_location,
    )
