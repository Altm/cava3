from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.application.simple_catalog.common import default_location
from app.models import models
from app.schemas import simple as schemas


@dataclass(frozen=True)
class SellProductCommand:
    payload: schemas.SaleRequest


@dataclass(frozen=True)
class SellWineGlassCommand:
    payload: schemas.SaleRequest


class SellProductHandler:
    def handle(self, command: SellProductCommand, uow: AbstractUnitOfWork) -> dict:
        db = uow.session
        sale_request = command.payload
        product = db.query(models.Product).get(sale_request.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        loc = default_location(db)
        stock = (
            db.query(models.Stock)
            .filter(models.Stock.location_id == loc.id, models.Stock.product_id == product.id)
            .with_for_update()
            .first()
        )
        if not stock or stock.quantity < sale_request.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")

        if product.product_type.is_composite:
            components = db.query(models.ProductComposite).filter(models.ProductComposite.parent_product_id == product.id).all()
            for comp in components:
                comp_stock = (
                    db.query(models.Stock)
                    .filter(models.Stock.location_id == loc.id, models.Stock.product_id == comp.component_product_id)
                    .with_for_update()
                    .first()
                )
                required = Decimal(str(comp.quantity)) * sale_request.quantity
                if not comp_stock or comp_stock.quantity < required:
                    raise HTTPException(status_code=400, detail="Insufficient stock for component")
                comp_stock.quantity -= required
        stock.quantity -= sale_request.quantity
        return {"message": f"Successfully sold {sale_request.quantity} of {product.name}"}


class SellWineGlassHandler:
    def handle(self, command: SellWineGlassCommand, uow: AbstractUnitOfWork) -> dict:
        db = uow.session
        sale_request = command.payload
        product = db.query(models.Product).get(sale_request.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        glasses_per_bottle = (
            db.query(models.ProductAttributeValue)
            .join(models.ProductAttribute, models.ProductAttributeValue.product_attribute_id == models.ProductAttribute.id)
            .filter(
                models.ProductAttributeValue.product_id == product.id,
                models.ProductAttribute.code == "glasses_per_bottle",
            )
            .first()
        )
        if not glasses_per_bottle or not glasses_per_bottle.value_number:
            raise HTTPException(status_code=400, detail="Missing glasses_per_bottle")
        bottles_needed = sale_request.quantity / glasses_per_bottle.value_number

        loc = default_location(db)
        stock = (
            db.query(models.Stock)
            .filter(models.Stock.location_id == loc.id, models.Stock.product_id == product.id)
            .with_for_update()
            .first()
        )
        if not stock or stock.quantity < bottles_needed:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        stock.quantity -= bottles_needed
        return {"message": f"Successfully sold {sale_request.quantity} glasses of {product.name}"}
