from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Base, Unit, ProductType, AttributeDefinition
from backend.database import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Единицы
        if not db.query(Unit).first():
            units = [
                Unit(symbol="л", name="литр"),
                Unit(symbol="мл", name="миллилитр", base_unit_id=1, conversion_factor=1000),
                Unit(symbol="кг", name="килограмм"),
                Unit(symbol="г", name="грамм", base_unit_id=3, conversion_factor=1000),
                Unit(symbol="шт", name="штука"),
                Unit(symbol="%", name="процент"),
            ]
            for u in units:
                db.add(u)
            db.flush()

            # Типы
            wine_type = ProductType(name="Вино", is_composite=False)
            olives_type = ProductType(name="Оливки", is_composite=False)
            sandwich_type = ProductType(name="Бутерброд", is_composite=True)

            db.add_all([wine_type, olives_type, sandwich_type])
            db.flush()

            # Атрибуты
            attrs = [
                AttributeDefinition(product_type_id=wine_type.id, name="Объём", code="volume", data_type="number", unit_id=1, is_required=True),
                AttributeDefinition(product_type_id=wine_type.id, name="Крепость", code="alcohol", data_type="number", unit_id=6, is_required=True),
                AttributeDefinition(product_type_id=wine_type.id, name="Порций на бутылку", code="servings", data_type="number", unit_id=5, is_required=True),

                AttributeDefinition(product_type_id=olives_type.id, name="Вес", code="weight", data_type="number", unit_id=3, is_required=True),
                AttributeDefinition(product_type_id=olives_type.id, name="Калорийность", code="calories", data_type="number", unit_id=None, is_required=True),
                AttributeDefinition(product_type_id=olives_type.id, name="Есть косточка", code="has_pit", data_type="boolean", is_required=True),
            ]
            db.add_all(attrs)
            db.commit()
    finally:
        db.close()