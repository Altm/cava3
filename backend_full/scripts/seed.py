from decimal import Decimal
from sqlalchemy.orm import Session
from app.infrastructure.db.session import SessionLocal
from app.models.models import (
    Unit,
    UnitConversion,
    ProductType,
    Product,
    ProductAttribute,
    ProductCategory,
    CompositeComponent,
    Location,
    PriceList,
    Terminal,
    User,
    Stock,
    Role,
    Permission,
    RolePermission,
    UserRole,
    InventorySnapshot,
    Adjustment,
    Transfer,
    SaleEvent,
    SaleLine,
)
from app.security.auth import get_password_hash


def upsert(session: Session, model, defaults=None, **kwargs):
    defaults = defaults or {}
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        for k, v in defaults.items():
            setattr(instance, k, v)
        return instance
    params = dict(kwargs, **defaults)
    instance = model(**params)
    session.add(instance)
    session.flush()
    return instance


def seed(db: Session):
    # Units and conversions
    bottle = upsert(db, Unit, code="bottle", defaults={"description": "Bottle"})
    glass = upsert(
        db, Unit, code="glass", defaults={"description": "Glass", "ratio_to_base": Decimal("0.2")}
    )
    gram = upsert(db, Unit, code="gram", defaults={"description": "Gram"})
    loaf_fraction = upsert(
        db, Unit, code="loaf_fraction", defaults={"description": "Loaf fraction", "discrete_step": Decimal("0.1")}
    )
    jar_fraction = upsert(
        db, Unit, code="jar_fraction", defaults={"description": "Jar fraction", "discrete_step": Decimal("0.1")}
    )
    upsert(
        db,
        UnitConversion,
        from_unit="glass",
        to_unit="bottle",
        defaults={"ratio": Decimal("0.2")},
    )

    # Product types
    wine_type = upsert(db, ProductType, name="wine", defaults={"description": "Wine"})
    bread_type = upsert(db, ProductType, name="bread", defaults={"description": "Bread"})
    snack_type = upsert(db, ProductType, name="snack", defaults={"description": "Snacks"})

    # Products
    merlot = upsert(
        db,
        Product,
        sku="WINE001",
        defaults={
            "name": "Merlot",
            "primary_category": "wine",
            "product_type_id": wine_type.id,
            "base_unit_code": "bottle",
            "is_composite": False,
        },
    )
    rioja = upsert(
        db,
        Product,
        sku="WINE002",
        defaults={
            "name": "Rioja Reserva",
            "primary_category": "wine",
            "product_type_id": wine_type.id,
            "base_unit_code": "bottle",
            "is_composite": False,
        },
    )
    baguette = upsert(
        db,
        Product,
        sku="BREAD001",
        defaults={
            "name": "Baguette",
            "primary_category": "bakery",
            "product_type_id": bread_type.id,
            "base_unit_code": "loaf_fraction",
            "is_composite": False,
        },
    )
    olive_jar = upsert(
        db,
        Product,
        sku="OLIVE001",
        defaults={
            "name": "Olive jar",
            "primary_category": "grocery",
            "product_type_id": snack_type.id,
            "base_unit_code": "jar_fraction",
            "is_composite": False,
        },
    )
    piece_unit = upsert(db, Unit, code="piece", defaults={"description": "Piece"})
    sandwich = upsert(
        db,
        Product,
        sku="SNACK001",
        defaults={
            "name": "Sandwich",
            "primary_category": "snack",
            "product_type_id": snack_type.id,
            "base_unit_code": piece_unit.code,
            "is_composite": True,
        },
    )
    tasting_set = upsert(
        db,
        Product,
        sku="SET001",
        defaults={
            "name": "Tasting set",
            "primary_category": "set",
            "product_type_id": snack_type.id,
            "base_unit_code": piece_unit.code,
            "is_composite": True,
        },
    )

    # Attributes and categories
    upsert(
        db,
        ProductAttribute,
        product_id=merlot.id,
        name="vintage_year",
        defaults={"value": "2018"},
    )
    upsert(
        db,
        ProductAttribute,
        product_id=merlot.id,
        name="glasses_per_bottle",
        defaults={"value": "5"},
    )
    upsert(
        db,
        ProductCategory,
        product_id=merlot.id,
        category="red",
        defaults={},
    )

    # Composite components
    upsert(
        db,
        CompositeComponent,
        parent_product_id=sandwich.id,
        component_product_id=baguette.id,
        defaults={"quantity": Decimal("0.1"), "unit_code": "loaf_fraction"},
    )
    upsert(
        db,
        CompositeComponent,
        parent_product_id=sandwich.id,
        component_product_id=olive_jar.id,
        defaults={"quantity": Decimal("0.1"), "unit_code": "jar_fraction"},
    )
    upsert(
        db,
        CompositeComponent,
        parent_product_id=tasting_set.id,
        component_product_id=merlot.id,
        defaults={"quantity": Decimal("2"), "unit_code": "glass"},
    )
    upsert(
        db,
        CompositeComponent,
        parent_product_id=tasting_set.id,
        component_product_id=sandwich.id,
        defaults={"quantity": Decimal("1"), "unit_code": "piece"},
    )

    # Locations
    bar = upsert(db, Location, name="Main bar", defaults={"kind": "bar"})
    warehouse = upsert(db, Location, name="Warehouse", defaults={"kind": "warehouse"})

    # Stocks
    upsert(
        db,
        Stock,
        location_id=bar.id,
        product_id=merlot.id,
        defaults={"quantity": Decimal("12"), "unit_code": "bottle"},
    )
    upsert(
        db,
        Stock,
        location_id=bar.id,
        product_id=baguette.id,
        defaults={"quantity": Decimal("5"), "unit_code": "loaf_fraction"},
    )
    upsert(
        db,
        Stock,
        location_id=bar.id,
        product_id=olive_jar.id,
        defaults={"quantity": Decimal("3"), "unit_code": "jar_fraction"},
    )
    upsert(
        db,
        Stock,
        location_id=warehouse.id,
        product_id=merlot.id,
        defaults={"quantity": Decimal("30"), "unit_code": "bottle"},
    )

    # Price lists
    for loc in (bar, warehouse):
        upsert(
            db,
            PriceList,
            location_id=loc.id,
            product_id=merlot.id,
            unit_code="bottle",
            defaults={"currency": "USD", "amount": Decimal("25")},
        )
        upsert(
            db,
            PriceList,
            location_id=loc.id,
            product_id=baguette.id,
            unit_code="loaf_fraction",
            defaults={"currency": "USD", "amount": Decimal("1.5")},
        )
        upsert(
            db,
            PriceList,
            location_id=loc.id,
            product_id=sandwich.id,
            unit_code="piece",
            defaults={"currency": "USD", "amount": Decimal("6")},
        )
        upsert(
            db,
            PriceList,
            location_id=loc.id,
            product_id=tasting_set.id,
            unit_code="piece",
            defaults={"currency": "USD", "amount": Decimal("12")},
        )

    # Terminals
    upsert(db, Terminal, terminal_id="T-1", defaults={"location_id": bar.id, "secret_hash": "secret"})
    upsert(db, Terminal, terminal_id="T-2", defaults={"location_id": warehouse.id, "secret_hash": "secret2"})

    # Users, roles, permissions
    admin = upsert(
        db,
        User,
        username="admin",
        defaults={
            "password_hash": get_password_hash("admin"),
            "is_superuser": True,
            "is_active": True,
        },
    )
    manager = upsert(
        db,
        User,
        username="manager",
        defaults={
            "password_hash": get_password_hash("manager"),
            "is_superuser": False,
            "is_active": True,
        },
    )
    perm_codes = [
        "product.read",
        "product.write",
        "stock.write",
        "user.read",
        "user.write",
    ]
    perms = {code: upsert(db, Permission, code=code) for code in perm_codes}
    role_mgr = upsert(db, Role, name="manager", defaults={"scope": "global"})
    for p in perms.values():
        upsert(db, RolePermission, role_id=role_mgr.id, permission_id=p.id)
    upsert(db, UserRole, user_id=manager.id, role_id=role_mgr.id)

    # Adjustments and transfers
    upsert(
        db,
        Adjustment,
        location_id=bar.id,
        product_id=merlot.id,
        defaults={"delta": Decimal("1"), "unit_code": "bottle", "reason": "Initial count"},
    )
    upsert(
        db,
        Transfer,
        from_location_id=warehouse.id,
        to_location_id=bar.id,
        product_id=merlot.id,
        defaults={"quantity": Decimal("3"), "unit_code": "bottle"},
    )

    # Inventory snapshot
    upsert(
        db,
        InventorySnapshot,
        location_id=bar.id,
        defaults={"data": {"note": "Initial snapshot", "items": []}},
    )

    # Sample sale
    sale_event = upsert(
        db,
        SaleEvent,
        event_id="seed-sale-1",
        defaults={
            "terminal_id": 1,
            "location_id": bar.id,
            "payload": {"lines": []},
            "status": "pending",
        },
    )
    upsert(
        db,
        SaleLine,
        sale_event_id=sale_event.id,
        product_id=merlot.id,
        defaults={
            "quantity": Decimal("1"),
            "unit_code": "bottle",
            "currency": "USD",
            "price": Decimal("25"),
        },
    )

    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
        print("Seed completed")
