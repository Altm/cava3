from decimal import Decimal
from sqlalchemy.orm import Session
from app.infrastructure.db.session import SessionLocal
from app.models.models import (
    Unit,
    UnitConversion,
    ProductType,
    Product,
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
    AttributeDefinition,
    ProductAttributeValue,
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
    # Units
    liter = upsert(db, Unit, code="liter", defaults={"description": "Литр"})
    kg = upsert(db, Unit, code="kg", defaults={"description": "Килограмм"})
    bottle = upsert(db, Unit, code="bottle", defaults={"description": "Бутылка"})
    glass = upsert(db, Unit, code="glass", defaults={"description": "Бокал", "ratio_to_base": Decimal("0.1667")})
    piece = upsert(db, Unit, code="piece", defaults={"description": "Штука"})
    upsert(db, UnitConversion, from_unit="glass", to_unit="bottle", defaults={"ratio": Decimal("0.1667")})

    # Product types
    wine_type = upsert(db, ProductType, name="Вино", defaults={"description": "Wine", "is_composite": False})
    olives_type = upsert(db, ProductType, name="Оливки", defaults={"description": "Olives", "is_composite": False})
    bread_type = upsert(db, ProductType, name="Хлеб", defaults={"description": "Bread", "is_composite": False})
    tomato_paste_type = upsert(db, ProductType, name="Томатная паста", defaults={"description": "Tomato paste", "is_composite": False})
    wine_basket_type = upsert(db, ProductType, name="Корзина вин", defaults={"description": "Wine basket", "is_composite": True})
    sandwich_type = upsert(db, ProductType, name="Бутерброд", defaults={"description": "Sandwich", "is_composite": True})
    tasting_set_type = upsert(db, ProductType, name="Дегустационный набор", defaults={"description": "Tasting set", "is_composite": True})

    # Attribute definitions
    volume_attr = upsert(
        db,
        AttributeDefinition,
        product_type_id=wine_type.id,
        code="volume",
        defaults={"name": "Объём", "data_type": "number", "unit_code": "liter", "is_required": True},
    )
    strength_attr = upsert(
        db,
        AttributeDefinition,
        product_type_id=wine_type.id,
        code="strength",
        defaults={"name": "Крепость", "data_type": "number", "is_required": True},
    )
    glasses_per_bottle_attr = upsert(
        db,
        AttributeDefinition,
        product_type_id=wine_type.id,
        code="glasses_per_bottle",
        defaults={"name": "Бокалов в бутылке", "data_type": "number", "is_required": False},
    )
    weight_attr = upsert(
        db,
        AttributeDefinition,
        product_type_id=olives_type.id,
        code="weight",
        defaults={"name": "Вес", "data_type": "number", "unit_code": "kg", "is_required": True},
    )
    calories_attr = upsert(
        db,
        AttributeDefinition,
        product_type_id=olives_type.id,
        code="calories",
        defaults={"name": "Калорийность", "data_type": "number", "is_required": True},
    )
    has_pit_attr = upsert(
        db,
        AttributeDefinition,
        product_type_id=olives_type.id,
        code="has_pit",
        defaults={"name": "С косточкой", "data_type": "boolean", "is_required": True},
    )
    bread_weight_attr = upsert(
        db,
        AttributeDefinition,
        product_type_id=bread_type.id,
        code="weight",
        defaults={"name": "Вес", "data_type": "number", "unit_code": "kg", "is_required": True},
    )
    paste_weight_attr = upsert(
        db,
        AttributeDefinition,
        product_type_id=tomato_paste_type.id,
        code="weight",
        defaults={"name": "Вес", "data_type": "number", "unit_code": "kg", "is_required": True},
    )

    def create_product(name: str, sku: str, ptype: ProductType, base_unit: str, unit_cost: Decimal, stock_qty: Decimal, attrs: dict):
        prod = upsert(
            db,
            Product,
            sku=sku,
            defaults={
                "name": name,
                "primary_category": ptype.name,
                "product_type_id": ptype.id,
                "base_unit_code": base_unit,
                "is_composite": ptype.is_composite,
                "unit_cost": unit_cost,
            },
        )
        db.query(ProductAttributeValue).filter(ProductAttributeValue.product_id == prod.id).delete()
        for attr_def, val in attrs.items():
            pav = ProductAttributeValue(
                product_id=prod.id,
                attribute_definition_id=attr_def.id,
                value_number=Decimal(str(val)) if attr_def.data_type == "number" else None,
                value_boolean=bool(val) if attr_def.data_type == "boolean" else None,
                value_string=str(val) if attr_def.data_type == "string" else None,
            )
            db.add(pav)
        return prod, stock_qty

    wines = []
    wines.append(create_product("Красное сухое вино", "WINE_R1", wine_type, "bottle", Decimal("500"), Decimal("10"), {volume_attr: 0.75, strength_attr: 12.5, glasses_per_bottle_attr: 6}))
    wines.append(create_product("Белое полусладкое вино", "WINE_W1", wine_type, "bottle", Decimal("400"), Decimal("5"), {volume_attr: 0.75, strength_attr: 11.0, glasses_per_bottle_attr: 6}))
    wines.append(create_product("Розовое вино", "WINE_P1", wine_type, "bottle", Decimal("450"), Decimal("8"), {volume_attr: 0.75, strength_attr: 13.0, glasses_per_bottle_attr: 6}))
    wines.append(create_product("Игристое вино", "WINE_S1", wine_type, "bottle", Decimal("600"), Decimal("6"), {volume_attr: 0.75, strength_attr: 12.0, glasses_per_bottle_attr: 6}))
    wines.append(create_product("Десертное вино", "WINE_D1", wine_type, "bottle", Decimal("700"), Decimal("4"), {volume_attr: 0.5, strength_attr: 15.0, glasses_per_bottle_attr: 4}))

    olives, olives_stock = create_product("Чёрные оливки", "OLIVE001", olives_type, "kg", Decimal("200"), Decimal("20"), {weight_attr: 0.5, calories_attr: 150.0, has_pit_attr: False})
    bread, bread_stock = create_product("Багет", "BREAD001", bread_type, "kg", Decimal("50"), Decimal("15"), {bread_weight_attr: 0.4})
    tomato_paste, tomato_stock = create_product("Томатная паста", "PASTE001", tomato_paste_type, "kg", Decimal("80"), Decimal("30"), {paste_weight_attr: 0.2})

    wine_basket = upsert(
        db,
        Product,
        sku="SET_WINE",
        defaults={
            "name": "Корзина из 5 вин",
            "primary_category": "Корзина вин",
            "product_type_id": wine_basket_type.id,
            "base_unit_code": "piece",
            "is_composite": True,
            "unit_cost": Decimal("2000"),
        },
    )
    sandwich = upsert(
        db,
        Product,
        sku="SNACK001",
        defaults={
            "name": "Бутерброд",
            "primary_category": "Бутерброд",
            "product_type_id": sandwich_type.id,
            "base_unit_code": "piece",
            "is_composite": True,
            "unit_cost": Decimal("30"),
        },
    )
    tasting_set = upsert(
        db,
        Product,
        sku="SET001",
        defaults={
            "name": "Дегустационный набор",
            "primary_category": "Дегустационный набор",
            "product_type_id": tasting_set_type.id,
            "base_unit_code": "piece",
            "is_composite": True,
            "unit_cost": Decimal("500"),
        },
    )

    for wine_prod, _ in wines:
        upsert(
            db,
            CompositeComponent,
            parent_product_id=wine_basket.id,
            component_product_id=wine_prod.id,
            defaults={"quantity": Decimal("1"), "unit_code": "bottle"},
        )
    upsert(db, CompositeComponent, parent_product_id=sandwich.id, component_product_id=bread.id, defaults={"quantity": Decimal("0.1"), "unit_code": "kg"})
    upsert(db, CompositeComponent, parent_product_id=sandwich.id, component_product_id=tomato_paste.id, defaults={"quantity": Decimal("0.02"), "unit_code": "kg"})
    for wine_prod, _ in wines:
        upsert(
            db,
            CompositeComponent,
            parent_product_id=tasting_set.id,
            component_product_id=wine_prod.id,
            defaults={"quantity": Decimal("0.167"), "unit_code": "bottle"},
        )
    upsert(db, CompositeComponent, parent_product_id=tasting_set.id, component_product_id=sandwich.id, defaults={"quantity": Decimal("1"), "unit_code": "piece"})

    default_loc = upsert(db, Location, name="Main", defaults={"kind": "bar"})
    stock_items = []
    for prod, qty in wines:
        stock_items.append((prod, qty, "bottle"))
    stock_items.append((olives, olives_stock, "kg"))
    stock_items.append((bread, bread_stock, "kg"))
    stock_items.append((tomato_paste, tomato_stock, "kg"))
    stock_items.append((wine_basket, Decimal("5"), "piece"))
    stock_items.append((sandwich, Decimal("50"), "piece"))
    stock_items.append((tasting_set, Decimal("10"), "piece"))
    for prod, qty, unit in stock_items:
        upsert(db, Stock, location_id=default_loc.id, product_id=prod.id, defaults={"quantity": qty, "unit_code": unit})
        upsert(db, PriceList, location_id=default_loc.id, product_id=prod.id, unit_code=unit, defaults={"currency": "EUR", "amount": prod.unit_cost})

    upsert(db, Terminal, terminal_id="T-1", defaults={"location_id": default_loc.id, "secret_hash": "secret"})

    admin = upsert(db, User, username="admin", defaults={"password_hash": get_password_hash("admin"), "is_superuser": True, "is_active": True})
    manager = upsert(db, User, username="manager", defaults={"password_hash": get_password_hash("manager"), "is_superuser": False, "is_active": True})
    perm_codes = ["product.read", "product.write", "stock.write", "user.read", "user.write"]
    perms = {code: upsert(db, Permission, code=code) for code in perm_codes}
    role_mgr = upsert(db, Role, name="manager", defaults={"scope": "global"})
    for p in perms.values():
        upsert(db, RolePermission, role_id=role_mgr.id, permission_id=p.id)
    upsert(db, UserRole, user_id=manager.id, role_id=role_mgr.id)

    upsert(db, Adjustment, location_id=default_loc.id, product_id=wines[0][0].id, defaults={"delta": Decimal("1"), "unit_code": "bottle", "reason": "Initial count"})
    upsert(db, Transfer, from_location_id=default_loc.id, to_location_id=default_loc.id, product_id=wines[0][0].id, defaults={"quantity": Decimal("0"), "unit_code": "bottle"})
    upsert(db, InventorySnapshot, location_id=default_loc.id, defaults={"data": {"note": "Initial snapshot", "items": []}})

    sale_event = upsert(db, SaleEvent, event_id="seed-sale-1", defaults={"terminal_id": 1, "location_id": default_loc.id, "payload": {"lines": []}, "status": "pending"})
    upsert(db, SaleLine, sale_event_id=sale_event.id, product_id=wines[0][0].id, defaults={"quantity": Decimal("1"), "unit_code": "bottle", "currency": "EUR", "price": Decimal("25")})

    db.commit()


def init_sample_data(db: Session):
    seed(db)


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
        print("Seed completed")
