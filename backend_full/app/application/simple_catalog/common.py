from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
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


def serialize_product(db_product: models.Product, db: Session) -> schemas.Product:
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

    total_stock_result = (
        db.query(func.coalesce(func.sum(models.Stock.quantity), Decimal("0")))
        .filter(models.Stock.product_id == db_product.id)
        .scalar()
    )
    total_stock = total_stock_result if total_stock_result is not None else Decimal("0")

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
    )


def serialize_product_view(db_product: models.Product, db: Session) -> schemas.ProductView:
    base = serialize_product(db_product, db)
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
    return schemas.ProductView(**base.model_dump(), meta=meta_out)
