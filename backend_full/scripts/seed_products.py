"""Seed script for importing wine products from CSV file with Shopify metadata

This script imports wine products from a CSV file, creates corresponding records in the database,
and handles Shopify metadata for each product.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import os
from urllib.parse import urlparse
from decimal import Decimal

# === IMPORT MODELS ===
from app.models.models import (
    Product, ProductType, ProductAttribute, ProductAttributeValue, 
    ProductCategory, Stock, ProductMeta, Unit
)
from app.infrastructure.db.base import Base
from app.config import get_settings


# === SETTINGS ===
CSV_FILE = "./data/products_normalized.csv"
DEFAULT_LOCATION_ID = 1  # ID of the default location/warehouse
DEFAULT_BASE_UNIT_CODE = "bottle"  # or "piece", "unit" — ensure it exists in the unit table

# === ATTRIBUTE MAPPING: CSV COLUMN → ATTRIBUTE CODE ===
ATTRIBUTE_MAPPING = {
    "alcohol_content_custom_alcohol": "alcohol",
    "appellation_area_custom_appellation": "appellation_area",
    "display_in_custom_display_in": "display_in",
    "warehouse_bin_custom_warehouse_bin": "warehouse_bin",
    "bio_filter_bio": "bio",
    "country_filter_country": "country",
    "grapes_filter_grapes": "grapes",
    "grapes_dominant_filter_grapes_dominant": "grapes_dominant",
    "type_filter_type": "type",
    "region_filters_region": "region",
    "pais_shopify_country": "pais",
    "preferencias_alimentarias_shopify_dietary_preferences": "preferencias_alimentarias",
    "region_shopify_region": "region_shopify",
    "dulzura_del_vino_shopify_wine_sweetness": "dulzura_del_vino",
    "variedad_de_vino_shopify_wine_variety": "variedad_de_vino",
    "variant_weight_unit": "variant_weight_unit",
    "cost_per_item": "cost_per_item",
    "status": "status",
}


def get_database_session():
    """Get database session using settings from config"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def ensure_wine_product_type(db):
    """Ensure that product type 'Wine' (ID=1) exists"""
    wine_type = db.query(ProductType).filter(ProductType.id == 1).first()
    if not wine_type:
        wine_type = ProductType(
            id=1,
            name='Wine',
            description='Alcoholic beverages - Wine',
            is_composite=False
        )
        db.add(wine_type)
        db.commit()
        print("✅ Created product_type 'Wine' with id=1")
    else:
        print("✔️ Product type 'Wine' already exists")


def ensure_attributes_exist(db):
    """Ensure that attributes for product_type_id=1 exist"""
    existing_attrs = {
        attr.code: attr.id for attr in 
        db.query(ProductAttribute).filter(ProductAttribute.product_type_id == 1).all()
    }

    for csv_col, attr_code in ATTRIBUTE_MAPPING.items():
        if attr_code not in existing_attrs:
            attr_name = attr_code.replace("_", " ").title()
            attr = ProductAttribute(
                product_type_id=1,
                name=attr_name,
                code=attr_code,
                data_type='string',
                is_required=False,
                sort_order=100
            )
            db.add(attr)
            db.commit()
            db.refresh(attr)  # Refresh to get the assigned ID
            existing_attrs[attr_code] = attr.id
            print(f"🆕 Created attribute: {attr_code} (id={attr.id})")
        else:
            print(f"✔️ Attribute already exists: {attr_code}")

    return existing_attrs  # {code: id}


def get_base_unit_id(db):
    """Get the ID of the base unit"""
    unit = db.query(Unit).filter(Unit.code == DEFAULT_BASE_UNIT_CODE).first()
    if not unit:
        raise Exception(f"Unit '{DEFAULT_BASE_UNIT_CODE}' not found in the unit table")
    return unit.id


def import_wines(db, df, attr_map, base_unit_id):
    """Main import function"""
    for idx, row in df.iterrows():
        # Skip non-wine products
        cat = str(row.get("product_category", "")).lower()
        title = str(row.get("title", "")).lower()
        if "wine" not in cat and "vin" not in title and "vino" not in title:
            continue

        old_id = row["old_id"]
        print(f"📦 Processing product old_id={old_id}, title={row['title']}")

        # --- 1. Create/update product ---
        unit_cost_str = row["variant_price"]
        unit_cost = Decimal(str(float(unit_cost_str))) if unit_cost_str not in ("", "nan") else Decimal("0.0")

        # Check if product exists by old_id via shopify meta
        meta = db.query(ProductMeta).filter(ProductMeta.old_id == old_id).first()
        
        if meta:
            # Update existing product
            product = db.query(Product).filter(Product.id == meta.product_id).first()
            if product:
                product.name = row["title"]
                product.unit_cost = unit_cost
                product.primary_category = "Wine"
                print(f"🔄 Updated product.id={product.id}")
        else:
            # Insert new product
            product = Product(
                name=row["title"],
                product_type_id=1,
                unit_cost=unit_cost,
                primary_category="Wine",
                is_active=True,
                base_unit_id=base_unit_id
            )
            db.add(product)
            db.commit()
            db.refresh(product)  # Refresh to get the assigned ID
            print(f"🆕 Created product.id={product.id}")

        # --- 2. Create/update product_meta ---
        meta_data = {
            "product_id": product.id,
            "old_id": old_id,
            "handle": row.get("handle", ""),
            "body_html": row.get("body_html", ""),
            "vendor": row.get("vendor", ""),
            "type": row.get("type", ""),
            "tags": row.get("tags", ""),
            "published": str(row.get("published", "")).lower() in ("true", "1", "yes"),
            "variant_barcode": row.get("variant_barcode", ""),
            "seo_title": row.get("seo_title", ""),
            "seo_description": row.get("seo_description", ""),
            "google_shopping": row.get("google_shopping_google_product_category", ""),
            "image": row.get("downloaded_image", ""),
        }

        if meta:
            # Update existing meta
            for key, value in meta_data.items():
                if key != "product_id":  # Don't update product_id
                    setattr(meta, key, value)
        else:
            # Create new meta
            meta = ProductMeta(**meta_data)
            db.add(meta)

        # --- 3. Attributes ---
        for csv_col, attr_code in ATTRIBUTE_MAPPING.items():
            value = row.get(csv_col, "")
            if value in ("", "nan", "None"):
                continue
            
            attr_id = attr_map[attr_code]
            
            # Check if attribute value already exists
            attr_value = db.query(ProductAttributeValue).filter(
                ProductAttributeValue.product_id == product.id,
                ProductAttributeValue.product_attribute_id == attr_id
            ).first()
            
            if attr_value:
                # Update existing value
                attr_value.value_string = str(value)
            else:
                # Create new attribute value
                attr_value = ProductAttributeValue(
                    product_id=product.id,
                    product_attribute_id=attr_id,
                    value_string=str(value)
                )
                db.add(attr_value)

        # --- 4. Category ---
        category = db.query(ProductCategory).filter(
            ProductCategory.product_id == product.id,
            ProductCategory.category == 'Wine'
        ).first()
        
        if not category:
            category = ProductCategory(
                product_id=product.id,
                category='Wine'
            )
            db.add(category)

        # --- 5. Stock ---
        stock = db.query(Stock).filter(
            Stock.location_id == DEFAULT_LOCATION_ID,
            Stock.product_id == product.id
        ).first()
        
        if not stock:
            stock = Stock(
                location_id=DEFAULT_LOCATION_ID,
                product_id=product.id,
                quantity=Decimal("0"),  # Default to 0
                unit_id=base_unit_id
            )
            db.add(stock)

        db.commit()
        print(f"✅ Processed product {product.name} (id={product.id})")

    print("✅ Import completed!")


def main():
    """Main function"""
    if not os.path.exists(CSV_FILE):
        raise FileNotFoundError(f"File {CSV_FILE} not found")

    # Create database session
    db = get_database_session()

    try:
        df = pd.read_csv(CSV_FILE, dtype=str)
        df = df.fillna("")

        ensure_wine_product_type(db)
        attr_map = ensure_attributes_exist(db)
        base_unit_id = get_base_unit_id(db)

        import_wines(db, df, attr_map, base_unit_id)
    finally:
        db.close()


if __name__ == "__main__":
    main()