"""Base seed script for Cavina.

Creates baseline entities for local/dev environments:
- units, locations;
- users, roles, permissions;
- terminals;
- products from CSV with product types/categories/meta/attributes;
- stock and prices for imported products.

The script is idempotent and can be re-run safely.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.models import (
    Location,
    Permission,
    PriceList,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductCategory,
    ProductMeta,
    ProductType,
    ProductTypeUnit,
    ProductUnit,
    Role,
    RolePermission,
    Stock,
    Terminal,
    Unit,
    User,
    UserRole,
)
from app.security.auth import get_password_hash


# ============================================================
# SETTINGS: what to create
# ============================================================

CREATE_UNITS = True
CREATE_LOCATIONS = True
CREATE_RBAC = True
CREATE_TERMINALS = True
CREATE_PRODUCTS_FROM_CSV = True
CREATE_STOCK = True
CREATE_PRICE_LIST = True

# CSV import settings
CSV_FILE = (os.getenv("SEED_CSV_FILE") or "").strip() or None
CSV_FILE_NAME = "products_normalized.csv"
DEFAULT_PRODUCT_TYPE_NAME = "General"
DEFAULT_BASE_UNIT_CODE = "bottle"
DEFAULT_CURRENCY = "EUR"

# Category import switches
IMPORT_WINE = True
IMPORT_BEER = True
IMPORT_SPIRITS = True
IMPORT_LIQUEURS = True
IMPORT_COCKTAILS = True
IMPORT_LOW_ALCOHOL_WINE = True
IMPORT_WATER = True
IMPORT_OLIVES = True
IMPORT_FOOD = True
IMPORT_OTHER = False

# Default users/roles
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
MANAGER_USERNAME = "manager"
MANAGER_PASSWORD = "manager"

# Location/terminal setup
WAREHOUSE_LOCATION_NAME = "Main Warehouse"
WAREHOUSE_LOCATION_CODE = "warehouse"
BAR_LOCATION_NAME = "Main Bar"
BAR_LOCATION_CODE = "bar"

TERMINALS = [
    {"terminal_id": "T-1", "location_code": BAR_LOCATION_CODE, "secret": "secret", "status": "active"},
]

# Minimal unit catalog
UNITS = [
    {"code": "bottle", "description": "Бутылка", "unit_type": "base", "is_discrete": True},
    {"code": "box", "description": "Коробка", "unit_type": "package", "is_discrete": True},
    {"code": "piece", "description": "Штука", "unit_type": "base", "is_discrete": True},
    {"code": "glass", "description": "Бокал", "unit_type": "portion", "is_discrete": False},
    {"code": "liter", "description": "Литр", "unit_type": "base", "is_discrete": False},
    {"code": "ml", "description": "Миллилитр", "unit_type": "portion", "is_discrete": False},
    {"code": "kg", "description": "Килограмм", "unit_type": "base", "is_discrete": False},
    {"code": "gram", "description": "Грамм", "unit_type": "portion", "is_discrete": False},
]

LOCATIONS = [
    {"name": WAREHOUSE_LOCATION_NAME, "code": WAREHOUSE_LOCATION_CODE, "is_active": True},
    {"name": BAR_LOCATION_NAME, "code": BAR_LOCATION_CODE, "is_active": True},
]

PERMISSION_CODES = [
    "attribute_definition.write",
    "boxes.read",
    "boxes.write",
    "catalog.read",
    "inventories.write",
    "location.read",
    "location.write",
    "product.delete",
    "product.read",
    "product.write",
    "product_type.delete",
    "product_type.read",
    "product_type.write",
    "qr.scan",
    "receipts.read",
    "receipts.write",
    "sale.write",
    "stock.write",
    "transfers.write",
    "unit.delete",
    "unit.read",
    "unit.write",
    "unit_conversion.read",
    "unit_conversion.write",
    "user.read",
    "user.write",
]

MANAGER_PERMISSION_CODES = [
    "catalog.read",
    "product.read",
    "product.write",
    "product_type.read",
    "product_type.write",
    "receipts.read",
    "receipts.write",
    "boxes.read",
    "boxes.write",
    "transfers.write",
    "inventories.write",
    "sale.write",
    "stock.write",
    "location.read",
    "unit.read",
    "unit.write",
    "user.read",
]

# Attribute mappings by product type.
# format: "attribute_code": {"type": "...", "columns": ("csv_column", "legacy_column")}
ATTRIBUTE_MAPPING_COMMON = {
    "display_in": {"type": "string", "columns": ("display_in_custom_display_in",)},
    "warehouse_bin": {"type": "string", "columns": ("warehouse_bin_custom_warehouse_bin",)},
    "status": {"type": "string", "columns": ("status",)},
    "cost_per_item": {"type": "number", "columns": ("cost_per_item",)},
}

ATTRIBUTE_MAPPING_WINE = {
    "alcohol": {"type": "number", "columns": ("alcohol_content_custom_alcohol",)},
    "appellation_area": {"type": "string", "columns": ("appellation_area_custom_appellation",)},
    "bio": {"type": "boolean", "columns": ("bio_filter_bio",)},
    "country": {"type": "string", "columns": ("country_filter_country",)},
    "grapes": {"type": "string", "columns": ("grapes_filter_grapes",)},
    "grapes_dominant": {"type": "string", "columns": ("grapes_dominant_filter_grapes-dominant", "grapes_dominant_filter_grapes_dominant")},
    "type": {"type": "string", "columns": ("type_filter_type",)},
    "region": {"type": "string", "columns": ("region_filters_region",)},
    "pais": {"type": "string", "columns": ("pais_shopify_country",)},
    "preferencias_alimentarias": {
        "type": "string",
        "columns": ("preferencias_alimentarias_shopify_dietary-preferences", "preferencias_alimentarias_shopify_dietary_preferences"),
    },
    "region_shopify": {"type": "string", "columns": ("region_shopify_region",)},
    "dulzura_del_vino": {"type": "string", "columns": ("dulzura_del_vino_shopify_wine-sweetness", "dulzura_del_vino_shopify_wine_sweetness")},
    "variedad_de_vino": {"type": "string", "columns": ("variedad_de_vino_shopify_wine-variety", "variedad_de_vino_shopify_wine_variety")},
    "variant_weight_unit": {"type": "string", "columns": ("variant_weight_unit",)},
}

ATTRIBUTE_MAPPING_BEER = {
    "alcohol": {"type": "number", "columns": ("alcohol_content_custom_alcohol",)},
    "country": {"type": "string", "columns": ("country_filter_country",)},
    "type": {"type": "string", "columns": ("type_filter_type",)},
    "region": {"type": "string", "columns": ("region_filters_region",)},
    "variant_weight_unit": {"type": "string", "columns": ("variant_weight_unit",)},
}

ATTRIBUTE_MAPPING_SPIRITS = {
    "alcohol": {"type": "number", "columns": ("alcohol_content_custom_alcohol",)},
    "country": {"type": "string", "columns": ("country_filter_country",)},
    "type": {"type": "string", "columns": ("type_filter_type",)},
    "region": {"type": "string", "columns": ("region_filters_region",)},
    "variant_weight_unit": {"type": "string", "columns": ("variant_weight_unit",)},
}

ATTRIBUTE_MAPPING_OLIVES = {
    "country": {"type": "string", "columns": ("country_filter_country",)},
    "bio": {"type": "boolean", "columns": ("bio_filter_bio",)},
    "type": {"type": "string", "columns": ("type_filter_type",)},
}

ATTRIBUTE_MAPPING_DEFAULT = {
    "type": {"type": "string", "columns": ("type_filter_type", "type")},
    "variant_weight_unit": {"type": "string", "columns": ("variant_weight_unit",)},
}


@dataclass
class SeedContext:
    units: dict[str, Unit]
    locations: dict[str, Location]
    permissions: dict[str, Permission]
    roles: dict[str, Role]
    users: dict[str, User]


def get_database_session() -> Session:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def upsert(session: Session, model, lookup: dict, updates: dict | None = None):
    updates = updates or {}
    instance = session.query(model).filter_by(**lookup).first()
    if instance:
        for key, value in updates.items():
            setattr(instance, key, value)
        return instance
    params = {**lookup, **updates}
    instance = model(**params)
    session.add(instance)
    session.flush()
    return instance


def normalize_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text and text.lower() != "nan" else default


def decimal_or(value: object, default: Decimal) -> Decimal:
    raw = normalize_text(value)
    if not raw:
        return default
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return default


def int_or_none(value: object) -> int | None:
    raw = normalize_text(value)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def maybe_bool(value: object) -> bool | None:
    raw = normalize_text(value).lower()
    if raw in {"", "none"}:
        return None
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    return None


IMPORT_FLAGS_BY_KEY = {
    "WINE": IMPORT_WINE,
    "BEER": IMPORT_BEER,
    "SPIRITS": IMPORT_SPIRITS,
    "LIQUEURS": IMPORT_LIQUEURS,
    "COCKTAILS": IMPORT_COCKTAILS,
    "LOW_ALCOHOL_WINE": IMPORT_LOW_ALCOHOL_WINE,
    "WATER": IMPORT_WATER,
    "OLIVES": IMPORT_OLIVES,
    "FOOD": IMPORT_FOOD,
    "OTHER": IMPORT_OTHER,
}


def _split_category_path(raw_category: str) -> list[str]:
    parts = [part.strip() for part in raw_category.split(">") if part.strip()]
    if parts:
        return parts
    fallback = raw_category.strip()
    return [fallback] if fallback else [DEFAULT_PRODUCT_TYPE_NAME]


def _category_import_key(raw_category: str, leaf: str) -> str:
    category = raw_category.lower()
    leaf_lower = leaf.lower()

    if "low alcohol" in category and "wine" in category:
        return "LOW_ALCOHOL_WINE"
    if "beer" in leaf_lower:
        return "BEER"
    if "liqueur" in leaf_lower:
        return "LIQUEURS"
    if "cocktail" in leaf_lower:
        return "COCKTAILS"
    if "spirit" in leaf_lower or "liquor" in leaf_lower:
        return "SPIRITS"
    if "wine" in leaf_lower:
        return "WINE"
    if "water" in leaf_lower:
        return "WATER"
    if "olive" in leaf_lower:
        return "OLIVES"
    if "food" in category:
        return "FOOD"
    return "OTHER"


def _should_import_category(import_key: str) -> bool:
    return bool(IMPORT_FLAGS_BY_KEY.get(import_key, IMPORT_OTHER))


def _attribute_mapping_for_key(import_key: str) -> dict[str, dict]:
    if import_key in {"WINE", "LOW_ALCOHOL_WINE"}:
        return {**ATTRIBUTE_MAPPING_COMMON, **ATTRIBUTE_MAPPING_WINE}
    if import_key == "BEER":
        return {**ATTRIBUTE_MAPPING_COMMON, **ATTRIBUTE_MAPPING_BEER}
    if import_key in {"SPIRITS", "LIQUEURS", "COCKTAILS"}:
        return {**ATTRIBUTE_MAPPING_COMMON, **ATTRIBUTE_MAPPING_SPIRITS}
    if import_key == "OLIVES":
        return {**ATTRIBUTE_MAPPING_COMMON, **ATTRIBUTE_MAPPING_OLIVES}
    return {**ATTRIBUTE_MAPPING_COMMON, **ATTRIBUTE_MAPPING_DEFAULT}


def _base_unit_code_for_key(import_key: str) -> str:
    if import_key in {"WINE", "LOW_ALCOHOL_WINE", "BEER", "SPIRITS", "LIQUEURS", "COCKTAILS", "WATER"}:
        return "bottle"
    if import_key in {"OLIVES", "FOOD"}:
        return "piece"
    return DEFAULT_BASE_UNIT_CODE


def _value_from_row(row: pd.Series, columns: tuple[str, ...]) -> str:
    for column in columns:
        value = normalize_text(row.get(column))
        if value:
            return value
    return ""


def resolve_csv_file() -> tuple[Path | None, list[Path]]:
    checked: list[Path] = []
    if CSV_FILE:
        explicit = Path(CSV_FILE)
        checked.append(explicit)
        if explicit.exists():
            return explicit, checked

    script_path = Path(__file__).resolve()
    candidates = [
        Path("/app/data") / CSV_FILE_NAME,
        script_path.parents[2] / "data" / CSV_FILE_NAME,
        script_path.parents[1] / "data" / CSV_FILE_NAME,
        Path.cwd() / "data" / CSV_FILE_NAME,
    ]
    for candidate in candidates:
        checked.append(candidate)
        if candidate.exists():
            return candidate, checked
    return None, checked


def slug_for_sku(value: str) -> str:
    allowed = []
    for char in value.upper():
        if char.isalnum():
            allowed.append(char)
        elif char in {" ", "-", "_", "."}:
            allowed.append("_")
    sku = "".join(allowed).strip("_")
    while "__" in sku:
        sku = sku.replace("__", "_")
    return sku[:64] if sku else "ITEM"


def ensure_units(session: Session) -> dict[str, Unit]:
    units: dict[str, Unit] = {}
    for unit_data in UNITS:
        code = unit_data["code"]
        unit = upsert(
            session,
            Unit,
            lookup={"code": code},
            updates={
                "description": unit_data["description"],
                "unit_type": unit_data["unit_type"],
                "is_discrete": unit_data["is_discrete"],
            },
        )
        units[code] = unit
    session.flush()
    print(f"✅ Units: {len(units)}")
    return units


def ensure_locations(session: Session) -> dict[str, Location]:
    locations: dict[str, Location] = {}
    for location_data in LOCATIONS:
        location = upsert(
            session,
            Location,
            lookup={"code": location_data["code"]},
            updates={"name": location_data["name"], "is_active": bool(location_data["is_active"])},
        )
        locations[location.code] = location
    session.flush()
    print(f"✅ Locations: {len(locations)}")
    return locations


def ensure_permissions(session: Session) -> dict[str, Permission]:
    permissions: dict[str, Permission] = {}
    for code in PERMISSION_CODES:
        permissions[code] = upsert(session, Permission, lookup={"code": code}, updates={"description": code})
    session.flush()
    print(f"✅ Permissions: {len(permissions)}")
    return permissions


def ensure_roles_and_users(
    session: Session,
    permissions: dict[str, Permission],
) -> tuple[dict[str, Role], dict[str, User]]:
    admin_role = upsert(session, Role, lookup={"name": "admin"}, updates={"scope": "global", "location_id": None})
    manager_role = upsert(session, Role, lookup={"name": "manager"}, updates={"scope": "global", "location_id": None})

    for permission in permissions.values():
        upsert(
            session,
            RolePermission,
            lookup={"role_id": admin_role.id, "permission_id": permission.id},
        )

    for code in MANAGER_PERMISSION_CODES:
        permission = permissions.get(code)
        if permission:
            upsert(
                session,
                RolePermission,
                lookup={"role_id": manager_role.id, "permission_id": permission.id},
            )

    admin = upsert(
        session,
        User,
        lookup={"username": ADMIN_USERNAME},
        updates={
            "password_hash": get_password_hash(ADMIN_PASSWORD),
            "is_active": True,
            "is_superuser": True,
        },
    )
    manager = upsert(
        session,
        User,
        lookup={"username": MANAGER_USERNAME},
        updates={
            "password_hash": get_password_hash(MANAGER_PASSWORD),
            "is_active": True,
            "is_superuser": False,
        },
    )

    upsert(session, UserRole, lookup={"user_id": admin.id, "role_id": admin_role.id})
    upsert(session, UserRole, lookup={"user_id": manager.id, "role_id": manager_role.id})
    session.flush()
    print("✅ Users/Roles seeded")
    return {"admin": admin_role, "manager": manager_role}, {"admin": admin, "manager": manager}


def ensure_terminals(session: Session, locations: dict[str, Location]) -> None:
    created = 0
    for terminal_data in TERMINALS:
        location = locations.get(terminal_data["location_code"])
        if not location:
            print(f"⚠️ Skip terminal {terminal_data['terminal_id']}: unknown location_code={terminal_data['location_code']}")
            continue
        upsert(
            session,
            Terminal,
            lookup={"terminal_id": terminal_data["terminal_id"]},
            updates={
                "location_id": location.id,
                "secret_hash": terminal_data["secret"],
                "status": terminal_data.get("status", "active"),
            },
        )
        created += 1
    session.flush()
    print(f"✅ Terminals: {created}")


def _row_category_context(row: pd.Series) -> tuple[str, str, list[str], str]:
    raw_category = normalize_text(row.get("product_category")) or normalize_text(row.get("type")) or DEFAULT_PRODUCT_TYPE_NAME
    categories = _split_category_path(raw_category)
    leaf = categories[-1][:100]
    import_key = _category_import_key(raw_category, leaf)
    return leaf, import_key, categories, raw_category


def _ensure_product_type(session: Session, leaf: str, raw_category: str) -> ProductType:
    product_type = upsert(
        session,
        ProductType,
        lookup={"name": leaf},
        updates={"description": raw_category[:255], "is_composite": False, "strict_units_by_type": False},
    )
    return product_type


def _ensure_type_attributes(
    session: Session,
    product_type: ProductType,
    mapping: dict[str, dict],
    units: dict[str, Unit],
    import_key: str,
) -> dict[str, ProductAttribute]:
    attrs: dict[str, ProductAttribute] = {}
    default_unit_code = _base_unit_code_for_key(import_key)
    default_unit = units.get(default_unit_code) or units.get(DEFAULT_BASE_UNIT_CODE)
    if not default_unit:
        raise RuntimeError(f"Unit not found for product type attributes: {default_unit_code}")
    for idx, (attr_code, attr_meta) in enumerate(mapping.items(), start=1):
        attribute = upsert(
            session,
            ProductAttribute,
            lookup={"product_type_id": product_type.id, "code": attr_code},
            updates={
                "name": attr_code.replace("_", " ").title(),
                "data_type": attr_meta["type"],
                "unit_id": default_unit.id,
                "is_required": False,
                "sort_order": idx,
            },
        )
        attrs[attr_code] = attribute
    return attrs


def _ensure_type_units(
    session: Session,
    product_type: ProductType,
    import_key: str,
    units: dict[str, Unit],
) -> None:
    base_unit_code = _base_unit_code_for_key(import_key)
    base_unit = units.get(base_unit_code) or units.get(DEFAULT_BASE_UNIT_CODE)
    if not base_unit:
        return
    upsert(
        session,
        ProductTypeUnit,
        lookup={"product_type_id": product_type.id, "unit_id": base_unit.id},
        updates={"ratio_to_base": Decimal("1"), "discrete_step": None},
    )
    if import_key in {"WINE", "LOW_ALCOHOL_WINE"} and units.get("glass"):
        upsert(
            session,
            ProductTypeUnit,
            lookup={"product_type_id": product_type.id, "unit_id": units["glass"].id},
            updates={"ratio_to_base": Decimal("0.2"), "discrete_step": Decimal("1")},
        )


def _upsert_product(
    session: Session,
    row: pd.Series,
    product_type: ProductType,
    import_key: str,
    category_labels: list[str],
    base_unit: Unit,
    warehouse: Location,
    units: dict[str, Unit],
) -> Product:
    title = normalize_text(row.get("title"), default="Unnamed product")
    old_id = int_or_none(row.get("old_id"))
    source_sku = normalize_text(row.get("variant_sku"))
    fallback_sku = slug_for_sku(f"{title}_{old_id or 'x'}")
    sku = (source_sku or fallback_sku)[:64]
    base_cost = decimal_or(row.get("variant_price"), default=Decimal("0"))

    product: Product | None = None
    meta_by_old_id = None
    if old_id is not None:
        meta_by_old_id = session.query(ProductMeta).filter(ProductMeta.old_id == old_id).first()
    if meta_by_old_id:
        product = session.query(Product).filter(Product.id == meta_by_old_id.product_id).first()
    if not product:
        product = session.query(Product).filter(Product.sku == sku).first()
    if not product:
        product = Product(
            name=title,
            sku=sku,
            primary_category=product_type.name[:64],
            product_type_id=product_type.id,
            base_unit_id=base_unit.id,
            is_active=True,
            base_cost=base_cost,
        )
        session.add(product)
        session.flush()
    else:
        product.name = title
        product.primary_category = product_type.name[:64]
        product.product_type_id = product_type.id
        product.base_unit_id = base_unit.id
        product.base_cost = base_cost
        product.is_active = True

    upsert(
        session,
        ProductUnit,
        lookup={"product_id": product.id, "unit_id": base_unit.id},
        updates={"ratio_to_base": Decimal("1"), "discrete_step": None},
    )

    upsert(
        session,
        ProductCategory,
        lookup={"product_id": product.id, "category": product_type.name[:64]},
    )
    for category in category_labels:
        category_name = category[:64]
        if category_name:
            upsert(
                session,
                ProductCategory,
                lookup={"product_id": product.id, "category": category_name},
            )

    if import_key in {"WINE", "LOW_ALCOHOL_WINE"} and units.get("glass"):
        upsert(
            session,
            ProductUnit,
            lookup={"product_id": product.id, "unit_id": units["glass"].id},
            updates={"ratio_to_base": Decimal("0.2"), "discrete_step": Decimal("1")},
        )

    if CREATE_STOCK:
        stock_qty = decimal_or(row.get("variant_inventory_qty"), default=Decimal("0"))
        upsert(
            session,
            Stock,
            lookup={"location_id": warehouse.id, "product_id": product.id},
            updates={"quantity": stock_qty, "unit_id": base_unit.id},
        )

    if CREATE_PRICE_LIST:
        amount = base_cost if base_cost > 0 else Decimal("0")
        upsert(
            session,
            PriceList,
            lookup={"location_id": warehouse.id, "product_id": product.id, "unit_id": base_unit.id},
            updates={"currency": DEFAULT_CURRENCY, "amount": amount},
        )

    meta_payload = {
        "old_id": old_id,
        "handle": normalize_text(row.get("handle")) or None,
        "body_html": normalize_text(row.get("body_html")) or None,
        "vendor": normalize_text(row.get("vendor")) or None,
        "type": normalize_text(row.get("type")) or None,
        "tags": normalize_text(row.get("tags")) or None,
        "published": maybe_bool(row.get("published")),
        "variant_barcode": normalize_text(row.get("variant_barcode")) or None,
        "seo_title": normalize_text(row.get("seo_title")) or None,
        "seo_description": normalize_text(row.get("seo_description")) or None,
        "google_shopping": normalize_text(row.get("google_shopping_google_product_category")) or None,
        "image": normalize_text(row.get("downloaded_image")) or None,
    }
    product_meta = session.query(ProductMeta).filter(ProductMeta.product_id == product.id).first()
    if not product_meta:
        product_meta = ProductMeta(product_id=product.id)
        session.add(product_meta)
        session.flush()
    for key, value in meta_payload.items():
        setattr(product_meta, key, value)

    return product


def _sync_product_attributes(
    session: Session,
    product: Product,
    row: pd.Series,
    attrs_by_code: dict[str, ProductAttribute],
    mapping: dict[str, dict],
) -> None:
    existing_values = {
        item.product_attribute_id: item
        for item in session.query(ProductAttributeValue).filter(ProductAttributeValue.product_id == product.id).all()
    }

    for attr_code, attr_meta in mapping.items():
        value = _value_from_row(row, tuple(attr_meta["columns"]))
        if not value:
            continue
        attr = attrs_by_code.get(attr_code)
        if not attr:
            continue

        pav = existing_values.get(attr.id)
        if not pav:
            pav = ProductAttributeValue(product_id=product.id, product_attribute_id=attr.id)
            session.add(pav)
            existing_values[attr.id] = pav
        attr_type = attr_meta["type"]
        pav.value_number = None
        pav.value_boolean = None
        pav.value_string = None
        if attr_type == "number":
            pav.value_number = float(decimal_or(value, Decimal("0")))
        elif attr_type == "boolean":
            bool_value = maybe_bool(value)
            pav.value_boolean = bool_value
        else:
            pav.value_string = value


def seed_products_from_csv(session: Session, units: dict[str, Unit], locations: dict[str, Location]) -> None:
    csv_file, checked_paths = resolve_csv_file()
    if not csv_file:
        checked = ", ".join(str(path) for path in checked_paths)
        print(f"⚠️ CSV not found, skip products. Checked: {checked}")
        return

    base_unit = units.get(DEFAULT_BASE_UNIT_CODE)
    if not base_unit:
        raise RuntimeError(f"Base unit not found: {DEFAULT_BASE_UNIT_CODE}")
    warehouse = locations.get(WAREHOUSE_LOCATION_CODE)
    if not warehouse:
        raise RuntimeError(f"Warehouse location not found: {WAREHOUSE_LOCATION_CODE}")

    df = pd.read_csv(csv_file, dtype=str).fillna("")
    created_or_updated = 0
    for _, row in df.iterrows():
        leaf, import_key, category_labels, raw_category = _row_category_context(row)
        if not _should_import_category(import_key):
            continue

        product_type = _ensure_product_type(session, leaf, raw_category)
        mapping = _attribute_mapping_for_key(import_key)
        attrs = _ensure_type_attributes(session, product_type, mapping, units, import_key)
        _ensure_type_units(session, product_type, import_key, units)

        product_base_unit_code = _base_unit_code_for_key(import_key)
        product_base_unit = units.get(product_base_unit_code) or base_unit
        product = _upsert_product(
            session=session,
            row=row,
            product_type=product_type,
            import_key=import_key,
            category_labels=category_labels,
            base_unit=product_base_unit,
            warehouse=warehouse,
            units=units,
        )
        _sync_product_attributes(session, product, row, attrs, mapping)
        created_or_updated += 1
    session.flush()
    print(f"✅ Products processed: {created_or_updated}")


def run_seed(session: Session) -> None:
    units: dict[str, Unit] = {}
    locations: dict[str, Location] = {}
    permissions: dict[str, Permission] = {}
    roles: dict[str, Role] = {}
    users: dict[str, User] = {}

    if CREATE_UNITS:
        units = ensure_units(session)

    if CREATE_LOCATIONS:
        locations = ensure_locations(session)

    if CREATE_RBAC:
        permissions = ensure_permissions(session)
        roles, users = ensure_roles_and_users(session, permissions)

    if CREATE_TERMINALS:
        if not locations:
            locations = ensure_locations(session)
        ensure_terminals(session, locations)

    if CREATE_PRODUCTS_FROM_CSV:
        if not units:
            units = ensure_units(session)
        if not locations:
            locations = ensure_locations(session)
        seed_products_from_csv(session, units, locations)

    session.commit()
    context = SeedContext(units=units, locations=locations, permissions=permissions, roles=roles, users=users)
    print(
        "✅ Seed base completed "
        f"(units={len(context.units)}, locations={len(context.locations)}, "
        f"permissions={len(context.permissions)}, roles={len(context.roles)}, users={len(context.users)})"
    )


def main() -> None:
    with get_database_session() as session:
        run_seed(session)


if __name__ == "__main__":
    main()
