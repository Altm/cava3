from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.application.simple_catalog.common import (
    ProductAvailabilityCalculator,
    default_location,
    serialize_product,
    serialize_product_view,
)
from app.models import models
from app.models.models import ProductAttribute, ProductAttributeValue, ProductMeta
from app.schemas import simple as schemas


@dataclass(frozen=True)
class CreateProductCommand:
    payload: schemas.ProductCreate


@dataclass(frozen=True)
class ListProductsQuery:
    location_id: Optional[int]
    product_type_id: Optional[int]
    name: Optional[str]
    skip: int
    limit: int


@dataclass(frozen=True)
class ProductsCountQuery:
    location_id: Optional[int]
    product_type_id: Optional[int]
    name: Optional[str]


@dataclass(frozen=True)
class GetProductQuery:
    product_id: int


@dataclass(frozen=True)
class GetProductViewQuery:
    product_id: int


@dataclass(frozen=True)
class UploadProductImageCommand:
    product_id: int
    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class UpdateProductCommand:
    product_id: int
    payload: schemas.ProductUpdate


@dataclass(frozen=True)
class DeleteProductCommand:
    product_id: int


def _assert_no_component_cycles(db, parent_product_id: int, component_product_ids: list[int]) -> None:
    if parent_product_id in component_product_ids:
        raise HTTPException(status_code=400, detail="Composite product cannot include itself")

    edges: dict[int, set[int]] = {}
    rows = db.query(models.ProductComposite.parent_product_id, models.ProductComposite.component_product_id).all()
    for parent_id, child_id in rows:
        if parent_id == parent_product_id:
            continue
        edges.setdefault(parent_id, set()).add(child_id)
    edges[parent_product_id] = set(component_product_ids)

    def reaches_target(start_id: int, target_id: int) -> bool:
        stack = [start_id]
        visited: set[int] = set()
        while stack:
            node = stack.pop()
            if node == target_id:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(edges.get(node, set()))
        return False

    for component_id in component_product_ids:
        if reaches_target(component_id, parent_product_id):
            raise HTTPException(status_code=400, detail="Composite cycle detected")


def _sync_product_units(
    db,
    *,
    product_id: int,
    base_unit_id: int,
    payload_units: list[schemas.ProductUnitCreate],
) -> None:
    desired_by_unit_id: dict[int, tuple[Decimal, Decimal | None]] = {
        base_unit_id: (Decimal("1"), None),
    }

    for unit in payload_units:
        if unit.unit_id == base_unit_id:
            continue
        unit_row = db.query(models.Unit).get(unit.unit_id)
        if not unit_row:
            raise HTTPException(status_code=400, detail=f"Unit not found: {unit.unit_id}")
        desired_by_unit_id[unit.unit_id] = (Decimal(str(unit.ratio_to_base)), unit.discrete_step)

    existing_rows = db.query(models.ProductUnit).filter(models.ProductUnit.product_id == product_id).all()
    existing_by_unit_id = {row.unit_id: row for row in existing_rows}

    for row in existing_rows:
        if row.unit_id not in desired_by_unit_id:
            db.delete(row)

    for unit_id, (ratio_to_base, discrete_step) in desired_by_unit_id.items():
        row = existing_by_unit_id.get(unit_id)
        if row:
            row.ratio_to_base = ratio_to_base
            row.discrete_step = discrete_step
            continue
        db.add(
            models.ProductUnit(
                product_id=product_id,
                unit_id=unit_id,
                ratio_to_base=ratio_to_base,
                discrete_step=discrete_step,
            )
        )


def _type_default_units(
    db,
    *,
    product_type_id: int,
) -> list[schemas.ProductUnitCreate]:
    rows = (
        db.query(models.ProductTypeUnit)
        .filter(models.ProductTypeUnit.product_type_id == product_type_id)
        .order_by(models.ProductTypeUnit.ratio_to_base.desc(), models.ProductTypeUnit.unit_id.asc())
        .all()
    )
    return [
        schemas.ProductUnitCreate(
            unit_id=row.unit_id,
            ratio_to_base=Decimal(str(row.ratio_to_base)),
            discrete_step=Decimal(str(row.discrete_step)) if row.discrete_step is not None else None,
        )
        for row in rows
    ]


def _units_payload_or_defaults(
    *,
    payload_units: list[schemas.ProductUnitCreate],
    default_units: list[schemas.ProductUnitCreate],
) -> list[schemas.ProductUnitCreate]:
    if payload_units:
        return payload_units
    return default_units


def _assert_strict_units(
    *,
    payload_units: list[schemas.ProductUnitCreate],
    allowed_unit_ids: set[int],
) -> None:
    for unit in payload_units:
        if unit.unit_id not in allowed_unit_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Unit {unit.unit_id} is not allowed by product type strict units",
            )


class CreateProductHandler:
    def handle(self, command: CreateProductCommand, uow: AbstractUnitOfWork) -> schemas.Product:
        db = uow.session
        product = command.payload

        base_unit = db.query(models.Unit).get(product.base_unit_id)
        if not base_unit:
            raise HTTPException(status_code=400, detail="Base unit not found")

        pt = db.query(models.ProductType).get(product.product_type_id)
        if not pt:
            raise HTTPException(status_code=400, detail="Product type not found")
        type_default_units = _type_default_units(db, product_type_id=pt.id)
        resolved_payload_units = _units_payload_or_defaults(
            payload_units=product.product_units or [],
            default_units=type_default_units,
        )
        if pt.strict_units_by_type:
            allowed_unit_ids = {row.unit_id for row in type_default_units}
            allowed_unit_ids.add(product.base_unit_id)
            _assert_strict_units(
                payload_units=resolved_payload_units,
                allowed_unit_ids=allowed_unit_ids,
            )

        db_product = models.Product(
            product_type_id=product.product_type_id,
            name=product.name,
            sku=product.sku or product.name.replace(" ", "_"),
            primary_category=pt.name,
            base_unit_id=product.base_unit_id,
            base_cost=product.base_cost,
            is_active=True,
        )
        db.add(db_product)
        db.flush()

        for attr in product.attributes:
            attr_def = db.get(ProductAttribute, attr.product_attribute_id)
            if not attr_def:
                raise ValueError("Invalid attribute definition")

            db_attr = ProductAttributeValue(
                product_id=db_product.id,
                product_attribute_id=attr.product_attribute_id,
            )

            if attr_def.data_type == "number":
                db_attr.value_number = float(attr.value) if attr.value is not None else None
            elif attr_def.data_type == "boolean":
                db_attr.value_boolean = bool(attr.value) if attr.value is not None else None
            elif attr_def.data_type == "string":
                db_attr.value_string = str(attr.value) if attr.value is not None else None

            db.add(db_attr)

        _sync_product_units(
            db,
            product_id=db_product.id,
            base_unit_id=product.base_unit_id,
            payload_units=resolved_payload_units,
        )

        if pt.is_composite:
            component_ids = [comp.component_product_id for comp in product.components]
            _assert_no_component_cycles(db, db_product.id, component_ids)
            for comp in product.components:
                component_product = db.query(models.Product).get(comp.component_product_id)
                if not component_product:
                    raise HTTPException(status_code=400, detail="Component product not found")
                db.add(
                    models.ProductComposite(
                        parent_product_id=db_product.id,
                        component_product_id=comp.component_product_id,
                        quantity=Decimal(str(comp.quantity)),
                        unit_id=component_product.base_unit_id,
                    )
                )

        loc = default_location(db)
        db.add(
            models.Stock(
                location_id=loc.id,
                product_id=db_product.id,
                quantity=Decimal(str(product.stock)),
                unit_id=product.base_unit_id,
            )
        )
        db.flush()
        return serialize_product(db_product, db)


class ListProductsHandler:
    def handle(self, query: ListProductsQuery, uow: AbstractUnitOfWork) -> list[schemas.Product]:
        db = uow.session
        query_builder = db.query(models.Product)

        if query.product_type_id:
            query_builder = query_builder.filter(models.Product.product_type_id == query.product_type_id)
        if query.name:
            query_builder = query_builder.filter(models.Product.name.ilike(f"%{query.name.strip()}%"))

        if query.location_id:
            subquery = (
                db.query(models.Stock.product_id)
                .filter(models.Stock.location_id == query.location_id)
                .distinct()
            )
            query_builder = query_builder.filter(models.Product.id.in_(subquery))

        products = query_builder.offset(query.skip).limit(query.limit).all()
        calculator = ProductAvailabilityCalculator(db, location_id=query.location_id)
        return [serialize_product(p, db, calculator=calculator) for p in products]


class ProductsCountHandler:
    def handle(self, query: ProductsCountQuery, uow: AbstractUnitOfWork) -> dict:
        db = uow.session
        query_builder = db.query(models.Product)

        if query.product_type_id:
            query_builder = query_builder.filter(models.Product.product_type_id == query.product_type_id)
        if query.name:
            query_builder = query_builder.filter(models.Product.name.ilike(f"%{query.name.strip()}%"))

        if query.location_id:
            subquery = (
                db.query(models.Stock.product_id)
                .filter(models.Stock.location_id == query.location_id)
                .distinct()
            )
            query_builder = query_builder.filter(models.Product.id.in_(subquery))

        return {"count": query_builder.count()}


class GetProductHandler:
    def handle(self, query: GetProductQuery, uow: AbstractUnitOfWork) -> schemas.Product:
        db = uow.session
        product = db.query(models.Product).get(query.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        calculator = ProductAvailabilityCalculator(db)
        return serialize_product(product, db, calculator=calculator)


class GetProductViewHandler:
    def handle(self, query: GetProductViewQuery, uow: AbstractUnitOfWork) -> schemas.ProductView:
        db = uow.session
        product = db.query(models.Product).get(query.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        calculator = ProductAvailabilityCalculator(db)
        return serialize_product_view(product, db, calculator=calculator)


class UploadProductImageHandler:
    def handle(self, command: UploadProductImageCommand, uow: AbstractUnitOfWork) -> schemas.ProductImageOut:
        db = uow.session
        product = db.query(models.Product).get(command.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if not command.content_type.startswith("image/"):
            raise HTTPException(status_code=422, detail="Only image files are allowed")

        suffix = Path(command.filename).suffix.lower()
        allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        if suffix not in allowed_suffixes:
            suffix = ".jpg"

        images_dir = Path("/app/data/product_images")
        images_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{command.product_id}_{uuid4().hex}{suffix}"
        output_path = images_dir / filename

        if not command.content:
            raise HTTPException(status_code=422, detail="Empty file")
        output_path.write_bytes(command.content)

        meta = db.query(ProductMeta).filter(ProductMeta.product_id == command.product_id).first()
        if not meta:
            meta = ProductMeta(product_id=command.product_id)
            db.add(meta)
            db.flush()

        meta.image = filename
        return schemas.ProductImageOut(image=filename, image_url=f"/images/{filename}")


class UpdateProductHandler:
    def handle(self, command: UpdateProductCommand, uow: AbstractUnitOfWork) -> schemas.Product:
        db = uow.session
        product = db.query(models.Product).get(command.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product_update = command.payload
        base_unit_id = product_update.base_unit_id if product_update.base_unit_id is not None else product.base_unit_id

        base_unit = db.query(models.Unit).get(base_unit_id)
        if not base_unit:
            raise HTTPException(status_code=400, detail="Base unit not found")

        pt = db.query(models.ProductType).get(product_update.product_type_id)
        if not pt:
            raise HTTPException(status_code=400, detail="Product type not found")
        type_default_units = _type_default_units(db, product_type_id=pt.id)
        resolved_payload_units = _units_payload_or_defaults(
            payload_units=product_update.product_units or [],
            default_units=type_default_units,
        )
        if pt.strict_units_by_type:
            allowed_unit_ids = {row.unit_id for row in type_default_units}
            allowed_unit_ids.add(base_unit_id)
            _assert_strict_units(
                payload_units=resolved_payload_units,
                allowed_unit_ids=allowed_unit_ids,
            )

        product.product_type_id = product_update.product_type_id
        product.name = product_update.name
        product.base_cost = product_update.base_cost
        product.base_unit_id = base_unit_id

        db.query(models.ProductAttributeValue).filter(models.ProductAttributeValue.product_id == product.id).delete()
        for attr in product_update.attributes:
            attr_def = db.get(ProductAttribute, attr.product_attribute_id)
            if not attr_def:
                raise ValueError("Invalid attribute definition")

            db_attr = models.ProductAttributeValue(
                product_id=product.id,
                product_attribute_id=attr.product_attribute_id,
            )
            if attr_def.data_type == "number":
                db_attr.value_number = float(attr.value) if attr.value is not None else None
            elif attr_def.data_type == "boolean":
                db_attr.value_boolean = bool(attr.value) if attr.value is not None else None
            elif attr_def.data_type == "string":
                db_attr.value_string = str(attr.value) if attr.value is not None else None
            db.add(db_attr)

        _sync_product_units(
            db,
            product_id=product.id,
            base_unit_id=base_unit_id,
            payload_units=resolved_payload_units,
        )

        db.query(models.ProductComposite).filter(models.ProductComposite.parent_product_id == product.id).delete()
        if pt.is_composite:
            component_ids = [comp.component_product_id for comp in product_update.components]
            _assert_no_component_cycles(db, product.id, component_ids)
            for comp in product_update.components:
                component_product = db.query(models.Product).get(comp.component_product_id)
                if not component_product:
                    raise HTTPException(status_code=400, detail="Component product not found")
                db.add(
                    models.ProductComposite(
                        parent_product_id=product.id,
                        component_product_id=comp.component_product_id,
                        quantity=Decimal(str(comp.quantity)),
                        unit_id=component_product.base_unit_id,
                    )
                )

        loc = default_location(db)
        stock = (
            db.query(models.Stock)
            .filter(models.Stock.location_id == loc.id, models.Stock.product_id == product.id)
            .first()
        )
        if stock:
            stock.quantity = Decimal(str(product_update.stock))
            stock.unit_id = base_unit_id
        else:
            db.add(
                models.Stock(
                    location_id=loc.id,
                    product_id=product.id,
                    quantity=Decimal(str(product_update.stock)),
                    unit_id=base_unit_id,
                )
            )
        db.flush()
        return serialize_product(product, db)


class DeleteProductHandler:
    def handle(self, command: DeleteProductCommand, uow: AbstractUnitOfWork) -> dict:
        db = uow.session
        product = db.query(models.Product).get(command.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        db.query(models.ProductAttributeValue).filter(models.ProductAttributeValue.product_id == product.id).delete()
        db.query(models.ProductComposite).filter(models.ProductComposite.parent_product_id == product.id).delete()
        db.delete(product)
        return {"message": "Product deleted successfully"}
