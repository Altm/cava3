from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException

from app.application.common.uow import AbstractUnitOfWork
from app.models import models
from app.schemas import simple as schemas


@dataclass(frozen=True)
class ListIngredientsQuery:
    name: Optional[str] = None


@dataclass(frozen=True)
class CreateIngredientCommand:
    payload: schemas.IngredientCreate


@dataclass(frozen=True)
class UpdateIngredientCommand:
    ingredient_id: int
    payload: schemas.IngredientUpdate


@dataclass(frozen=True)
class ListIngredientBindingsQuery:
    ingredient_id: int
    location_id: Optional[int] = None
    include_inactive: bool = False


@dataclass(frozen=True)
class CreateIngredientBindingCommand:
    ingredient_id: int
    payload: schemas.IngredientBindingCreate


@dataclass(frozen=True)
class UpdateIngredientBindingCommand:
    ingredient_id: int
    binding_id: int
    payload: schemas.IngredientBindingUpdate


@dataclass(frozen=True)
class DeleteIngredientBindingCommand:
    ingredient_id: int
    binding_id: int


class ListIngredientsHandler:
    def handle(self, query: ListIngredientsQuery, uow: AbstractUnitOfWork) -> list[schemas.IngredientOut]:
        db = uow.session
        query_builder = db.query(models.Ingredient).order_by(models.Ingredient.name.asc(), models.Ingredient.id.asc())
        if query.name:
            query_builder = query_builder.filter(models.Ingredient.name.ilike(f"%{query.name.strip()}%"))
        rows = query_builder.all()
        return [
            schemas.IngredientOut(
                id=row.id,
                code=row.code,
                name=row.name,
                base_unit_id=row.base_unit_id,
                description=row.description,
                is_active=bool(row.is_active),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]


class CreateIngredientHandler:
    def handle(self, command: CreateIngredientCommand, uow: AbstractUnitOfWork) -> schemas.IngredientOut:
        db = uow.session
        payload = command.payload
        existing = db.query(models.Ingredient).filter(models.Ingredient.code == payload.code).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ingredient code already exists")
        unit = db.get(models.Unit, payload.base_unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Base unit not found")
        row = models.Ingredient(
            code=payload.code.strip(),
            name=payload.name.strip(),
            base_unit_id=payload.base_unit_id,
            description=(payload.description or None),
            is_active=bool(payload.is_active),
        )
        db.add(row)
        db.flush()
        return schemas.IngredientOut(
            id=row.id,
            code=row.code,
            name=row.name,
            base_unit_id=row.base_unit_id,
            description=row.description,
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class UpdateIngredientHandler:
    def handle(self, command: UpdateIngredientCommand, uow: AbstractUnitOfWork) -> schemas.IngredientOut:
        db = uow.session
        payload = command.payload
        row = db.get(models.Ingredient, command.ingredient_id)
        if not row:
            raise HTTPException(status_code=404, detail="Ingredient not found")

        code = payload.code.strip()
        name = payload.name.strip()

        existing = (
            db.query(models.Ingredient)
            .filter(
                models.Ingredient.code == code,
                models.Ingredient.id != command.ingredient_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Ingredient code already exists")

        unit = db.get(models.Unit, payload.base_unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Base unit not found")

        row.code = code
        row.name = name
        row.base_unit_id = payload.base_unit_id
        row.description = payload.description or None
        row.is_active = bool(payload.is_active)
        db.flush()

        return schemas.IngredientOut(
            id=row.id,
            code=row.code,
            name=row.name,
            base_unit_id=row.base_unit_id,
            description=row.description,
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class ListIngredientBindingsHandler:
    def handle(self, query: ListIngredientBindingsQuery, uow: AbstractUnitOfWork) -> list[schemas.IngredientBindingOut]:
        db = uow.session
        ingredient = db.get(models.Ingredient, query.ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")
        query_builder = (
            db.query(models.IngredientProductBinding, models.Product.name)
            .join(models.Product, models.Product.id == models.IngredientProductBinding.product_id)
            .filter(models.IngredientProductBinding.ingredient_id == query.ingredient_id)
            .order_by(
                models.IngredientProductBinding.priority.asc(),
                models.IngredientProductBinding.location_id.desc().nulls_last(),
                models.IngredientProductBinding.id.asc(),
            )
        )
        if query.location_id is not None:
            query_builder = query_builder.filter(
                (models.IngredientProductBinding.location_id.is_(None))
                | (models.IngredientProductBinding.location_id == query.location_id)
            )
        if not query.include_inactive:
            query_builder = query_builder.filter(models.IngredientProductBinding.is_active.is_(True))
        rows = query_builder.all()
        return [
            schemas.IngredientBindingOut(
                id=binding.id,
                ingredient_id=binding.ingredient_id,
                product_id=binding.product_id,
                product_name=product_name,
                ratio_to_ingredient_base=binding.ratio_to_ingredient_base,
                priority=binding.priority,
                location_id=binding.location_id,
                valid_from=binding.valid_from,
                valid_to=binding.valid_to,
                is_active=bool(binding.is_active),
                created_at=binding.created_at,
                updated_at=binding.updated_at,
            )
            for binding, product_name in rows
        ]


class CreateIngredientBindingHandler:
    def handle(self, command: CreateIngredientBindingCommand, uow: AbstractUnitOfWork) -> schemas.IngredientBindingOut:
        db = uow.session
        ingredient = db.get(models.Ingredient, command.ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")
        payload = command.payload
        product = db.get(models.Product, payload.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        existing = (
            db.query(models.IngredientProductBinding)
            .filter(
                models.IngredientProductBinding.ingredient_id == command.ingredient_id,
                models.IngredientProductBinding.product_id == payload.product_id,
                models.IngredientProductBinding.location_id == payload.location_id,
                models.IngredientProductBinding.valid_from == payload.valid_from,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Binding already exists for this scope")

        row = models.IngredientProductBinding(
            ingredient_id=command.ingredient_id,
            product_id=payload.product_id,
            ratio_to_ingredient_base=payload.ratio_to_ingredient_base,
            priority=payload.priority,
            location_id=payload.location_id,
            valid_from=payload.valid_from,
            valid_to=payload.valid_to,
            is_active=bool(payload.is_active),
        )
        db.add(row)
        db.flush()
        return schemas.IngredientBindingOut(
            id=row.id,
            ingredient_id=row.ingredient_id,
            product_id=row.product_id,
            product_name=product.name,
            ratio_to_ingredient_base=row.ratio_to_ingredient_base,
            priority=row.priority,
            location_id=row.location_id,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class UpdateIngredientBindingHandler:
    def handle(self, command: UpdateIngredientBindingCommand, uow: AbstractUnitOfWork) -> schemas.IngredientBindingOut:
        db = uow.session
        ingredient = db.get(models.Ingredient, command.ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")

        row = (
            db.query(models.IngredientProductBinding)
            .filter(
                models.IngredientProductBinding.id == command.binding_id,
                models.IngredientProductBinding.ingredient_id == command.ingredient_id,
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Binding not found")

        payload = command.payload
        product = db.get(models.Product, payload.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        existing = (
            db.query(models.IngredientProductBinding)
            .filter(
                models.IngredientProductBinding.ingredient_id == command.ingredient_id,
                models.IngredientProductBinding.product_id == payload.product_id,
                models.IngredientProductBinding.location_id == payload.location_id,
                models.IngredientProductBinding.valid_from == payload.valid_from,
                models.IngredientProductBinding.id != command.binding_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Binding already exists for this scope")

        row.product_id = payload.product_id
        row.ratio_to_ingredient_base = payload.ratio_to_ingredient_base
        row.priority = payload.priority
        row.location_id = payload.location_id
        row.valid_from = payload.valid_from
        row.valid_to = payload.valid_to
        row.is_active = bool(payload.is_active)
        db.flush()

        return schemas.IngredientBindingOut(
            id=row.id,
            ingredient_id=row.ingredient_id,
            product_id=row.product_id,
            product_name=product.name,
            ratio_to_ingredient_base=row.ratio_to_ingredient_base,
            priority=row.priority,
            location_id=row.location_id,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class DeleteIngredientBindingHandler:
    def handle(self, command: DeleteIngredientBindingCommand, uow: AbstractUnitOfWork) -> dict:
        db = uow.session
        row = (
            db.query(models.IngredientProductBinding)
            .filter(
                models.IngredientProductBinding.id == command.binding_id,
                models.IngredientProductBinding.ingredient_id == command.ingredient_id,
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Binding not found")
        db.delete(row)
        return {"message": "Binding deleted"}
