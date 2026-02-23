from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models import models


class CompositeCycleError(Exception):
    def __init__(self, product_id: int, path: list[int]):
        super().__init__(f"Composite cycle detected at product_id={product_id}")
        self.product_id = product_id
        self.path = path


@dataclass
class ComponentRequirement:
    product_id: int
    product_name: str
    quantity_base: Decimal
    unit_code: str
    is_serial: bool
    path: list[int]


class CompositeDecompositionService:
    """Decompose composite product into leaf requirements in base units."""

    def __init__(self, db: Session):
        self.db = db
        self._decompose_cache: dict[tuple[int, str], list[ComponentRequirement]] = {}
        self._product_cache: dict[int, models.Product] = {}
        self._unit_code_cache: dict[int, str] = {}
        self._serial_cache: dict[int, bool] = {}
        self._ratio_cache: dict[tuple[int, int], Decimal] = {}
        self._components_cache: dict[tuple[int, Optional[str]], list] = {}

    def decompose(
        self,
        *,
        product_id: int,
        quantity_base: Decimal,
        visited: frozenset[int] = frozenset(),
        path: Optional[list[int]] = None,
        as_of: Optional[datetime] = None,
    ) -> list[ComponentRequirement]:
        if quantity_base <= 0:
            return []

        current_path = list(path or [])
        if product_id in visited:
            raise CompositeCycleError(product_id=product_id, path=current_path + [product_id])

        cache_key = (product_id, self._norm_decimal(quantity_base))
        if not visited and cache_key in self._decompose_cache:
            return [self._clone(req) for req in self._decompose_cache[cache_key]]

        product = self._get_product(product_id)
        components = self._get_components(product_id=product_id, as_of=as_of)
        is_composite = bool(product.product_type and product.product_type.is_composite)

        if not is_composite or not components:
            leaf = ComponentRequirement(
                product_id=product.id,
                product_name=product.name,
                quantity_base=quantity_base,
                unit_code=self._base_unit_code(product.base_unit_id),
                is_serial=self._is_serial(product),
                path=current_path + [product.id],
            )
            result = [leaf]
            if not visited:
                self._decompose_cache[cache_key] = [self._clone(leaf)]
            return result

        next_visited = visited | {product.id}
        next_path = current_path + [product.id]
        requirements: list[ComponentRequirement] = []
        for comp in components:
            component_product = self._get_product(comp.component_product_id)
            ratio_to_base = self._ratio_to_base(component_product, comp.unit_id)
            waste_factor = Decimal(str(getattr(comp, "waste_factor", 0) or 0))
            effective_quantity = Decimal(str(comp.quantity)) * (Decimal("1") + waste_factor)
            component_qty_base = quantity_base * effective_quantity * ratio_to_base
            requirements.extend(
                self.decompose(
                    product_id=component_product.id,
                    quantity_base=component_qty_base,
                    visited=next_visited,
                    path=next_path,
                    as_of=as_of,
                )
            )

        aggregated = self._aggregate(requirements)
        if not visited:
            self._decompose_cache[cache_key] = [self._clone(req) for req in aggregated]
        return aggregated

    def _get_components(self, *, product_id: int, as_of: Optional[datetime]) -> list:
        as_of_key = as_of.isoformat() if as_of else None
        cache_key = (product_id, as_of_key)
        cached = self._components_cache.get(cache_key)
        if cached is not None:
            return cached

        if hasattr(models, "ProductRecipe") and hasattr(models, "ProductRecipeComponent"):
            point_in_time = as_of or datetime.utcnow()
            rows = (
                self.db.query(models.ProductRecipeComponent)
                .join(models.ProductRecipe, models.ProductRecipe.id == models.ProductRecipeComponent.recipe_id)
                .filter(
                    models.ProductRecipe.product_id == product_id,
                    models.ProductRecipe.is_active.is_(True),
                    models.ProductRecipe.valid_from <= point_in_time,
                    (models.ProductRecipe.valid_to.is_(None) | (models.ProductRecipe.valid_to > point_in_time)),
                )
                .order_by(models.ProductRecipeComponent.id.asc())
                .all()
            )
            if rows:
                self._components_cache[cache_key] = rows
                return rows

        rows = (
            self.db.query(models.ProductComposite)
            .filter(models.ProductComposite.parent_product_id == product_id)
            .order_by(models.ProductComposite.id.asc())
            .all()
        )
        self._components_cache[cache_key] = rows
        return rows

    def _get_product(self, product_id: int) -> models.Product:
        cached = self._product_cache.get(product_id)
        if cached is not None:
            return cached
        product = self.db.query(models.Product).get(product_id)
        if product is None:
            raise ValueError(f"Product not found: {product_id}")
        self._product_cache[product_id] = product
        return product

    def _base_unit_code(self, unit_id: int) -> str:
        cached = self._unit_code_cache.get(unit_id)
        if cached is not None:
            return cached
        unit = self.db.query(models.Unit).get(unit_id)
        if unit is None:
            return f"unit:{unit_id}"
        self._unit_code_cache[unit_id] = unit.code
        return unit.code

    def _is_serial(self, product: models.Product) -> bool:
        cached = self._serial_cache.get(product.id)
        if cached is not None:
            return cached
        unit = self.db.query(models.Unit).get(product.base_unit_id)
        value = bool(unit and unit.is_discrete)
        self._serial_cache[product.id] = value
        return value

    def _ratio_to_base(self, product: models.Product, unit_id: int) -> Decimal:
        key = (product.id, unit_id)
        cached = self._ratio_cache.get(key)
        if cached is not None:
            return cached
        if unit_id == product.base_unit_id:
            ratio = Decimal("1")
        else:
            product_row = (
                self.db.query(models.ProductUnit.ratio_to_base)
                .filter(
                    models.ProductUnit.product_id == product.id,
                    models.ProductUnit.unit_id == unit_id,
                )
                .first()
            )
            if product_row:
                ratio = Decimal(str(product_row[0]))
            elif product.product_type_id:
                type_row = (
                    self.db.query(models.ProductTypeUnit.ratio_to_base)
                    .filter(
                        models.ProductTypeUnit.product_type_id == product.product_type_id,
                        models.ProductTypeUnit.unit_id == unit_id,
                    )
                    .first()
                )
                if type_row:
                    ratio = Decimal(str(type_row[0]))
                else:
                    raise ValueError(f"Missing product unit conversion for product={product.id}, unit={unit_id}")
            else:
                raise ValueError(f"Missing product unit conversion for product={product.id}, unit={unit_id}")
        self._ratio_cache[key] = ratio
        return ratio

    @staticmethod
    def _norm_decimal(value: Decimal) -> str:
        return format(value.normalize(), "f")

    @staticmethod
    def _clone(requirement: ComponentRequirement) -> ComponentRequirement:
        return ComponentRequirement(
            product_id=requirement.product_id,
            product_name=requirement.product_name,
            quantity_base=Decimal(str(requirement.quantity_base)),
            unit_code=requirement.unit_code,
            is_serial=requirement.is_serial,
            path=list(requirement.path),
        )

    @staticmethod
    def _aggregate(requirements: list[ComponentRequirement]) -> list[ComponentRequirement]:
        grouped: dict[int, ComponentRequirement] = {}
        for req in requirements:
            existing = grouped.get(req.product_id)
            if existing is None:
                grouped[req.product_id] = CompositeDecompositionService._clone(req)
            else:
                existing.quantity_base += req.quantity_base
        return list(grouped.values())
