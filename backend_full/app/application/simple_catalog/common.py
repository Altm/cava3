from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import models
from app.models.models import ProductMeta
from app.schemas import simple as schemas


def _normalize_decimal_output(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0")
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if decimal_value == 0:
        return Decimal("0")
    return decimal_value


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
        self._component_cache: dict[int, list] = {}
        self._ingredient_cache: dict[int, models.Ingredient] = {}
        self._ingredient_binding_cache: dict[int, list[models.IngredientProductBinding]] = {}
        self._ingredient_available_cache: dict[int, Decimal] = {}
        self._ratio_cache: dict[tuple[int, int], Optional[Decimal]] = {}
        self._stock_base_cache: dict[int, Decimal] = {}
        self._available_cache: dict[int, Decimal] = {}
        self._unit_discrete_cache: dict[int, bool] = {}
        self._unit_cache: dict[int, models.Unit] = {}

    def unit(self, unit_id: int) -> Optional[models.Unit]:
        cached = self._unit_cache.get(unit_id)
        if cached is not None:
            return cached
        unit = self.db.get(models.Unit, unit_id)
        if unit:
            self._unit_cache[unit_id] = unit
        return unit

    def product(self, product_id: int) -> Optional[models.Product]:
        cached = self._product_cache.get(product_id)
        if cached is not None:
            return cached
        product = self.db.get(models.Product, product_id)
        if product:
            self._product_cache[product_id] = product
        return product

    def ingredient(self, ingredient_id: int) -> Optional[models.Ingredient]:
        cached = self._ingredient_cache.get(ingredient_id)
        if cached is not None:
            return cached
        ingredient = self.db.get(models.Ingredient, ingredient_id)
        if ingredient:
            self._ingredient_cache[ingredient_id] = ingredient
        return ingredient

    def ingredient_bindings(self, ingredient_id: int) -> list[models.IngredientProductBinding]:
        cached = self._ingredient_binding_cache.get(ingredient_id)
        if cached is not None:
            return cached
        now = datetime.utcnow()
        query_builder = (
            self.db.query(models.IngredientProductBinding)
            .filter(
                models.IngredientProductBinding.ingredient_id == ingredient_id,
                models.IngredientProductBinding.is_active.is_(True),
                (models.IngredientProductBinding.valid_from.is_(None) | (models.IngredientProductBinding.valid_from <= now)),
                (models.IngredientProductBinding.valid_to.is_(None) | (models.IngredientProductBinding.valid_to > now)),
            )
        )
        if self.location_id is not None:
            query_builder = query_builder.filter(
                (models.IngredientProductBinding.location_id.is_(None))
                | (models.IngredientProductBinding.location_id == self.location_id)
            )
        rows = (
            query_builder.order_by(
                models.IngredientProductBinding.priority.asc(),
                models.IngredientProductBinding.location_id.desc().nulls_last(),
                models.IngredientProductBinding.id.asc(),
            ).all()
        )
        self._ingredient_binding_cache[ingredient_id] = rows
        return rows

    def components(self, product_id: int) -> list[models.ProductRecipeComponent]:
        cached = self._component_cache.get(product_id)
        if cached is not None:
            return cached
        now = datetime.utcnow()
        recipe_rows = (
            self.db.query(models.ProductRecipeComponent)
            .join(models.ProductRecipe, models.ProductRecipe.id == models.ProductRecipeComponent.recipe_id)
            .filter(
                models.ProductRecipe.product_id == product_id,
                models.ProductRecipe.is_active.is_(True),
                models.ProductRecipe.valid_from <= now,
                (models.ProductRecipe.valid_to.is_(None) | (models.ProductRecipe.valid_to > now)),
            )
            .order_by(models.ProductRecipeComponent.id.asc())
            .all()
        )
        self._component_cache[product_id] = recipe_rows
        return recipe_rows

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
        total_base = _normalize_decimal_output(total_base)
        self._stock_base_cache[product.id] = total_base
        return total_base

    def _base_unit_is_discrete(self, product: models.Product) -> bool:
        if product.id in self._unit_discrete_cache:
            return self._unit_discrete_cache[product.id]
        unit = self.unit(product.base_unit_id)
        value = bool(unit.is_discrete) if unit else False
        self._unit_discrete_cache[product.id] = value
        return value

    def ingredient_available_quantity(self, ingredient_id: int, stack: Optional[set[int]] = None) -> Decimal:
        if ingredient_id in self._ingredient_available_cache:
            return self._ingredient_available_cache[ingredient_id]
        ingredient = self.ingredient(ingredient_id)
        if not ingredient:
            return Decimal("0")
        total = Decimal("0")
        for binding in self.ingredient_bindings(ingredient_id):
            product = self.product(binding.product_id)
            if not product:
                continue
            product_available_base = self.available_quantity(product.id, stack=stack)
            ratio = Decimal(str(binding.ratio_to_ingredient_base or 0))
            if ratio <= 0:
                continue
            total += product_available_base * ratio
        total = _normalize_decimal_output(total)
        self._ingredient_available_cache[ingredient_id] = total
        return total

    def available_quantity(self, product_id: int, stack: Optional[set[int]] = None) -> Decimal:
        if product_id in self._available_cache:
            return self._available_cache[product_id]
        product = self.product(product_id)
        if not product:
            return Decimal("0")

        own_stock_base = self._sum_stock_base(product)
        if not product.product_type or not product.product_type.is_composite:
            own_stock_base = _normalize_decimal_output(own_stock_base)
            self._available_cache[product_id] = own_stock_base
            return own_stock_base

        components = self.components(product_id)
        if not components:
            own_stock_base = _normalize_decimal_output(own_stock_base)
            self._available_cache[product_id] = own_stock_base
            return own_stock_base

        active_stack = stack or set()
        if product_id in active_stack:
            return Decimal("0")
        active_stack.add(product_id)
        try:
            min_bundles: Optional[Decimal] = None
            for comp in components:
                ingredient = self.ingredient(comp.ingredient_id)
                if not ingredient:
                    min_bundles = Decimal("0")
                    break
                required_qty = Decimal(str(comp.quantity or 0))
                required_qty *= Decimal("1") + Decimal(str(getattr(comp, "waste_factor", 0) or 0))
                if required_qty <= 0:
                    continue
                if comp.unit_id != ingredient.base_unit_id:
                    min_bundles = Decimal("0")
                    break
                ingredient_available_base = self.ingredient_available_quantity(ingredient.id, stack=active_stack)
                bundles = ingredient_available_base / required_qty
                if min_bundles is None or bundles < min_bundles:
                    min_bundles = bundles
            if min_bundles is None:
                min_bundles = Decimal("0")
            if self._base_unit_is_discrete(product):
                available = min_bundles.to_integral_value(rounding=ROUND_DOWN)
            else:
                available = min_bundles.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
            available = _normalize_decimal_output(available)
            self._available_cache[product_id] = available
            return available
        finally:
            active_stack.remove(product_id)


def _serialize_product_units(db_product: models.Product) -> list[schemas.ProductUnit]:
    if db_product.product_units:
        rows = sorted(
            db_product.product_units or [],
            key=lambda unit: (
                Decimal(str(unit.ratio_to_base or 0)),
                unit.unit_id,
            ),
            reverse=True,
        )
        result = [
            schemas.ProductUnit(
                id=row.id,
                product_id=row.product_id,
                unit_id=row.unit_id,
                ratio_to_base=Decimal(str(row.ratio_to_base)),
                discrete_step=Decimal(str(row.discrete_step)) if row.discrete_step is not None else None,
                source="product",
            )
            for row in rows
        ]
        base_unit_exists = any(row.unit_id == db_product.base_unit_id for row in result)
        if not base_unit_exists:
            result.append(
                schemas.ProductUnit(
                    id=None,
                    product_id=db_product.id,
                    unit_id=db_product.base_unit_id,
                    ratio_to_base=Decimal("1"),
                    discrete_step=None,
                    source="base",
                )
            )
        return sorted(result, key=lambda row: (Decimal(str(row.ratio_to_base)), row.unit_id), reverse=True)

    type_units = sorted(
        db_product.product_type.product_type_units if db_product.product_type else [],
        key=lambda unit: (
            Decimal(str(unit.ratio_to_base or 0)),
            unit.unit_id,
        ),
        reverse=True,
    )
    result = [
        schemas.ProductUnit(
            id=None,
            product_id=db_product.id,
            unit_id=row.unit_id,
            ratio_to_base=Decimal(str(row.ratio_to_base)),
            discrete_step=Decimal(str(row.discrete_step)) if row.discrete_step is not None else None,
            source="type",
        )
        for row in type_units
    ]
    if not any(row.unit_id == db_product.base_unit_id for row in result):
        result.append(
            schemas.ProductUnit(
                id=None,
                product_id=db_product.id,
                unit_id=db_product.base_unit_id,
                ratio_to_base=Decimal("1"),
                discrete_step=None,
                source="base",
            )
        )
    return sorted(result, key=lambda row: (Decimal(str(row.ratio_to_base)), row.unit_id), reverse=True)


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
        ingredient = calculator.ingredient(component.ingredient_id)
        if not ingredient:
            continue
        for binding in calculator.ingredient_bindings(ingredient.id):
            _collect_product_tree_ids(calculator, binding.product_id, visited)
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
        base_quantity = _normalize_decimal_output(location_calc.available_quantity(db_product.id))
        unit_quantities = [
            schemas.ProductStockUnitQuantity(
                unit_id=row.unit_id,
                unit_code=unit_meta[row.unit_id].code if row.unit_id in unit_meta else str(row.unit_id),
                ratio_to_base=row.ratio_to_base,
                quantity=_normalize_decimal_output(
                    (base_quantity / Decimal(str(row.ratio_to_base))).quantize(Decimal("0.000001"))
                    if Decimal(str(row.ratio_to_base)) > 0
                    else Decimal("0")
                ),
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
            parent_product_id=db_product.id,
            ingredient_id=c.ingredient_id,
            ingredient_name=(c.ingredient.name if c.ingredient else None),
            quantity=c.quantity,
            unit_id=c.unit_id,
            substitution_allowed=c.substitution_allowed,
            rounding=c.rounding,
            waste_factor=Decimal(str(c.waste_factor or 0)),
        )
        for c in calc.components(db_product.id)
    ]
    product_units = _serialize_product_units(db_product)

    total_stock = _normalize_decimal_output(calc.available_quantity(db_product.id))

    return schemas.Product(
        id=db_product.id,
        product_type_id=db_product.product_type_id,
        name=db_product.name,
        base_cost=db_product.base_cost or Decimal("0"),
        default_portion_size=Decimal(str(db_product.default_portion_size)) if db_product.default_portion_size is not None else None,
        portions_per_unit=db_product.portions_per_unit,
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
        ingredient = calculator.ingredient(comp.ingredient_id)
        if not ingredient:
            continue
        unit = calculator.unit(comp.unit_id)
        bindings = calculator.ingredient_bindings(ingredient.id)
        primary_binding = bindings[0] if bindings else None
        bound_product = calculator.product(primary_binding.product_id) if primary_binding else None
        is_cycle = bool(bound_product and bound_product.id in chain)
        children: list[schemas.ProductComponentTreeNode] = []
        if bound_product and bound_product.product_type and bound_product.product_type.is_composite and not is_cycle:
            next_chain = set(chain)
            next_chain.add(bound_product.id)
            children = _build_component_tree(
                bound_product.id,
                db,
                calculator=calculator,
                path=next_chain,
            )
        result.append(
            schemas.ProductComponentTreeNode(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                quantity=Decimal(str(comp.quantity or 0)),
                unit_id=comp.unit_id,
                unit_code=unit.code if unit else None,
                bound_product_id=(bound_product.id if bound_product else None),
                bound_product_name=(bound_product.name if bound_product else None),
                bound_product_is_composite=bool(bound_product and bound_product.product_type and bound_product.product_type.is_composite),
                available_quantity=_normalize_decimal_output(calculator.ingredient_available_quantity(ingredient.id, stack=chain)),
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
