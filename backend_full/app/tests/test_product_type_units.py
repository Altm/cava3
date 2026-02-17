from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.application.simple_catalog.product_types import (
    CreateProductTypeCommand,
    CreateProductTypeHandler,
)
from app.application.simple_catalog.products import (
    CreateProductCommand,
    CreateProductHandler,
)
from app.infrastructure.db.uow import BoundSessionUnitOfWork
from app.models.models import ProductUnit, Unit
from app.schemas import simple as schemas


def _seed_units(db_session):
    bottle = Unit(code="bottle", description="Bottle", unit_type="base", is_discrete=True)
    glass = Unit(code="glass", description="Glass", unit_type="portion", is_discrete=True)
    box = Unit(code="box", description="Box", unit_type="package", is_discrete=True)
    db_session.add_all([bottle, glass, box])
    db_session.flush()
    return bottle, glass, box


def test_create_product_inherits_units_from_type_defaults(db_session):
    bottle, glass, _box = _seed_units(db_session)

    with BoundSessionUnitOfWork(db_session) as uow:
        product_type = CreateProductTypeHandler().handle(
            CreateProductTypeCommand(
                payload=schemas.ProductTypeCreate(
                    name="Wine",
                    is_composite=False,
                    strict_units_by_type=False,
                    product_type_units=[
                        schemas.ProductTypeUnitCreate(unit_id=glass.id, ratio_to_base=Decimal("0.2")),
                    ],
                )
            ),
            uow,
        )

    with BoundSessionUnitOfWork(db_session) as uow:
        product = CreateProductHandler().handle(
            CreateProductCommand(
                payload=schemas.ProductCreate(
                    product_type_id=product_type.id,
                    name="Wine A",
                    sku="W-A",
                    base_cost=Decimal("10.00"),
                    stock=Decimal("0"),
                    base_unit_id=bottle.id,
                    product_units=[],
                )
            ),
            uow,
        )

    rows = (
        db_session.query(ProductUnit)
        .filter(ProductUnit.product_id == product.id)
        .order_by(ProductUnit.unit_id.asc())
        .all()
    )
    by_unit = {row.unit_id: Decimal(str(row.ratio_to_base)) for row in rows}
    assert by_unit[bottle.id] == Decimal("1")
    assert by_unit[glass.id] == Decimal("0.2")


def test_strict_type_units_block_extra_product_units(db_session):
    bottle, glass, box = _seed_units(db_session)

    with BoundSessionUnitOfWork(db_session) as uow:
        product_type = CreateProductTypeHandler().handle(
            CreateProductTypeCommand(
                payload=schemas.ProductTypeCreate(
                    name="StrictWine",
                    is_composite=False,
                    strict_units_by_type=True,
                    product_type_units=[
                        schemas.ProductTypeUnitCreate(unit_id=glass.id, ratio_to_base=Decimal("0.2")),
                    ],
                )
            ),
            uow,
        )

    with pytest.raises(HTTPException) as exc:
        with BoundSessionUnitOfWork(db_session) as uow:
            CreateProductHandler().handle(
                CreateProductCommand(
                    payload=schemas.ProductCreate(
                        product_type_id=product_type.id,
                        name="Wine B",
                        sku="W-B",
                        base_cost=Decimal("12.00"),
                        stock=Decimal("0"),
                        base_unit_id=bottle.id,
                        product_units=[
                            schemas.ProductUnitCreate(unit_id=box.id, ratio_to_base=Decimal("6")),
                        ],
                    )
                ),
                uow,
            )
    assert exc.value.status_code == 400
    assert "not allowed by product type strict units" in str(exc.value.detail)


def test_non_strict_type_allows_extra_product_units(db_session):
    bottle, glass, box = _seed_units(db_session)

    with BoundSessionUnitOfWork(db_session) as uow:
        product_type = CreateProductTypeHandler().handle(
            CreateProductTypeCommand(
                payload=schemas.ProductTypeCreate(
                    name="FlexibleWine",
                    is_composite=False,
                    strict_units_by_type=False,
                    product_type_units=[
                        schemas.ProductTypeUnitCreate(unit_id=glass.id, ratio_to_base=Decimal("0.2")),
                    ],
                )
            ),
            uow,
        )

    with BoundSessionUnitOfWork(db_session) as uow:
        product = CreateProductHandler().handle(
            CreateProductCommand(
                payload=schemas.ProductCreate(
                    product_type_id=product_type.id,
                    name="Wine C",
                    sku="W-C",
                    base_cost=Decimal("13.00"),
                    stock=Decimal("0"),
                    base_unit_id=bottle.id,
                    product_units=[
                        schemas.ProductUnitCreate(unit_id=box.id, ratio_to_base=Decimal("6")),
                    ],
                )
            ),
            uow,
        )

    box_row = (
        db_session.query(ProductUnit)
        .filter(ProductUnit.product_id == product.id, ProductUnit.unit_id == box.id)
        .first()
    )
    assert box_row is not None
