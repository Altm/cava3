from sqlalchemy.orm import Session
import models
import database
import schemas

def init_sample_data(db: Session):
    # Create units
    liter = models.Unit(symbol="л", name="Литр")
    kg = models.Unit(symbol="кг", name="Килограмм")
    bottle = models.Unit(symbol="шт", name="Штука")
    
    db.add(liter)
    db.add(kg)
    db.add(bottle)
    db.commit()
    
    # Get the IDs after commit
    liter = db.query(models.Unit).filter(models.Unit.symbol == "л").first()
    kg = db.query(models.Unit).filter(models.Unit.symbol == "кг").first()
    bottle = db.query(models.Unit).filter(models.Unit.symbol == "шт").first()
    
    # Create product types
    wine_type = models.ProductType(name="Вино", is_composite=False)
    olives_type = models.ProductType(name="Оливки", is_composite=False)
    wine_basket_type = models.ProductType(name="Корзина вин", is_composite=True)
    
    db.add(wine_type)
    db.add(olives_type)
    db.add(wine_basket_type)
    db.commit()
    
    # Get the IDs after commit
    wine_type = db.query(models.ProductType).filter(models.ProductType.name == "Вино").first()
    olives_type = db.query(models.ProductType).filter(models.ProductType.name == "Оливки").first()
    wine_basket_type = db.query(models.ProductType).filter(models.ProductType.name == "Корзина вин").first()
    
    # Create attributes for wine
    volume_attr = models.AttributeDefinition(
        product_type_id=wine_type.id,
        name="Объём",
        code="volume",
        data_type="number",
        unit_id=liter.id,
        is_required=True
    )
    strength_attr = models.AttributeDefinition(
        product_type_id=wine_type.id,
        name="Крепость",
        code="strength",
        data_type="number",
        is_required=True
    )
    glasses_per_bottle_attr = models.AttributeDefinition(
        product_type_id=wine_type.id,
        name="Стаканов из бутылки",
        code="glasses_per_bottle",
        data_type="number",
        is_required=False
    )
    
    db.add(volume_attr)
    db.add(strength_attr)
    db.add(glasses_per_bottle_attr)
    db.commit()
    
    # Create attributes for olives
    weight_attr = models.AttributeDefinition(
        product_type_id=olives_type.id,
        name="Вес",
        code="weight",
        data_type="number",
        unit_id=kg.id,
        is_required=True
    )
    calories_attr = models.AttributeDefinition(
        product_type_id=olives_type.id,
        name="Калорийность",
        code="calories",
        data_type="number",
        is_required=True
    )
    has_pit_attr = models.AttributeDefinition(
        product_type_id=olives_type.id,
        name="С косточкой",
        code="has_pit",
        data_type="boolean",
        is_required=True
    )
    
    db.add(weight_attr)
    db.add(calories_attr)
    db.add(has_pit_attr)
    db.commit()
    
    # Create some sample products
    wine1 = models.Product(
        product_type_id=wine_type.id,
        name="Красное сухое вино",
        stock=10,
        unit_cost=500.0
    )
    wine2 = models.Product(
        product_type_id=wine_type.id,
        name="Белое полусладкое вино",
        stock=5,
        unit_cost=400.0
    )
    olives1 = models.Product(
        product_type_id=olives_type.id,
        name="Чёрные оливки",
        stock=20,
        unit_cost=200.0
    )
    
    db.add(wine1)
    db.add(wine2)
    db.add(olives1)
    db.commit()
    
    # Add attributes for wine1
    db.add(models.ProductAttributeValue(
        product_id=wine1.id,
        attribute_definition_id=volume_attr.id,
        value_number=0.75
    ))
    db.add(models.ProductAttributeValue(
        product_id=wine1.id,
        attribute_definition_id=strength_attr.id,
        value_number=12.5
    ))
    db.add(models.ProductAttributeValue(
        product_id=wine1.id,
        attribute_definition_id=glasses_per_bottle_attr.id,
        value_number=6.0
    ))
    
    # Add attributes for wine2
    db.add(models.ProductAttributeValue(
        product_id=wine2.id,
        attribute_definition_id=volume_attr.id,
        value_number=0.75
    ))
    db.add(models.ProductAttributeValue(
        product_id=wine2.id,
        attribute_definition_id=strength_attr.id,
        value_number=11.0
    ))
    
    # Add attributes for olives1
    db.add(models.ProductAttributeValue(
        product_id=olives1.id,
        attribute_definition_id=weight_attr.id,
        value_number=0.5
    ))
    db.add(models.ProductAttributeValue(
        product_id=olives1.id,
        attribute_definition_id=calories_attr.id,
        value_number=150.0
    ))
    db.add(models.ProductAttributeValue(
        product_id=olives1.id,
        attribute_definition_id=has_pit_attr.id,
        value_boolean=False
    ))
    
    db.commit()
    
    print("Sample data initialized successfully!")

if __name__ == "__main__":
    db = database.SessionLocal()
    try:
        init_sample_data(db)
    finally:
        db.close()