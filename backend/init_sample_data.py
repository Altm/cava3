from sqlalchemy.orm import Session
import models
import database
import schemas

def init_sample_data(db: Session):
    # Check if data already exists
    existing_product_types = db.query(models.ProductType).count()
    if existing_product_types > 0:
        print("Sample data already exists, skipping initialization")
        return

    # Create units
    liter = models.Unit(symbol="л", name="Литр")
    kg = models.Unit(symbol="кг", name="Килограмм")
    bottle = models.Unit(symbol="шт", name="Штука")
    glass = models.Unit(symbol="ст", name="Стакан")
    
    db.add(liter)
    db.add(kg)
    db.add(bottle)
    db.add(glass)
    db.commit()
    db.refresh(liter)
    db.refresh(kg)
    db.refresh(bottle)
    db.refresh(glass)
    
    # Create product types
    wine_type = models.ProductType(name="Вино", is_composite=False)
    olives_type = models.ProductType(name="Оливки", is_composite=False)
    bread_type = models.ProductType(name="Хлеб", is_composite=False)
    tomato_paste_type = models.ProductType(name="Томатная паста", is_composite=False)
    wine_basket_type = models.ProductType(name="Корзина вин", is_composite=True)
    sandwich_type = models.ProductType(name="Бутерброд", is_composite=True)
    tasting_set_type = models.ProductType(name="Дегустационный набор", is_composite=True)
    
    db.add(wine_type)
    db.add(olives_type)
    db.add(bread_type)
    db.add(tomato_paste_type)
    db.add(wine_basket_type)
    db.add(sandwich_type)
    db.add(tasting_set_type)
    db.commit()
    db.refresh(wine_type)
    db.refresh(olives_type)
    db.refresh(bread_type)
    db.refresh(tomato_paste_type)
    db.refresh(wine_basket_type)
    db.refresh(sandwich_type)
    db.refresh(tasting_set_type)
    
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
    db.refresh(volume_attr)
    db.refresh(strength_attr)
    db.refresh(glasses_per_bottle_attr)
    
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
    db.refresh(weight_attr)
    db.refresh(calories_attr)
    db.refresh(has_pit_attr)
    
    # Create attributes for bread
    bread_weight_attr = models.AttributeDefinition(
        product_type_id=bread_type.id,
        name="Вес",
        code="weight",
        data_type="number",
        unit_id=kg.id,
        is_required=True
    )
    
    db.add(bread_weight_attr)
    db.commit()
    db.refresh(bread_weight_attr)
    
    # Create attributes for tomato paste
    paste_weight_attr = models.AttributeDefinition(
        product_type_id=tomato_paste_type.id,
        name="Вес",
        code="weight",
        data_type="number",
        unit_id=kg.id,
        is_required=True
    )
    
    db.add(paste_weight_attr)
    db.commit()
    db.refresh(paste_weight_attr)
    
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
    wine3 = models.Product(
        product_type_id=wine_type.id,
        name="Розовое вино",
        stock=8,
        unit_cost=450.0
    )
    wine4 = models.Product(
        product_type_id=wine_type.id,
        name="Игристое вино",
        stock=6,
        unit_cost=600.0
    )
    wine5 = models.Product(
        product_type_id=wine_type.id,
        name="Десертное вино",
        stock=4,
        unit_cost=700.0
    )
    olives1 = models.Product(
        product_type_id=olives_type.id,
        name="Чёрные оливки",
        stock=20,
        unit_cost=200.0
    )
    bread1 = models.Product(
        product_type_id=bread_type.id,
        name="Багет",
        stock=15,
        unit_cost=50.0
    )
    tomato_paste1 = models.Product(
        product_type_id=tomato_paste_type.id,
        name="Томатная паста",
        stock=30,
        unit_cost=80.0
    )
    
    db.add(wine1)
    db.add(wine2)
    db.add(wine3)
    db.add(wine4)
    db.add(wine5)
    db.add(olives1)
    db.add(bread1)
    db.add(tomato_paste1)
    db.commit()
    db.refresh(wine1)
    db.refresh(wine2)
    db.refresh(wine3)
    db.refresh(wine4)
    db.refresh(wine5)
    db.refresh(olives1)
    db.refresh(bread1)
    db.refresh(tomato_paste1)
    
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
    db.add(models.ProductAttributeValue(
        product_id=wine2.id,
        attribute_definition_id=glasses_per_bottle_attr.id,
        value_number=6.0
    ))
    
    # Add attributes for wine3
    db.add(models.ProductAttributeValue(
        product_id=wine3.id,
        attribute_definition_id=volume_attr.id,
        value_number=0.75
    ))
    db.add(models.ProductAttributeValue(
        product_id=wine3.id,
        attribute_definition_id=strength_attr.id,
        value_number=13.0
    ))
    db.add(models.ProductAttributeValue(
        product_id=wine3.id,
        attribute_definition_id=glasses_per_bottle_attr.id,
        value_number=6.0
    ))
    
    # Add attributes for wine4
    db.add(models.ProductAttributeValue(
        product_id=wine4.id,
        attribute_definition_id=volume_attr.id,
        value_number=0.75
    ))
    db.add(models.ProductAttributeValue(
        product_id=wine4.id,
        attribute_definition_id=strength_attr.id,
        value_number=12.0
    ))
    db.add(models.ProductAttributeValue(
        product_id=wine4.id,
        attribute_definition_id=glasses_per_bottle_attr.id,
        value_number=6.0
    ))
    
    # Add attributes for wine5
    db.add(models.ProductAttributeValue(
        product_id=wine5.id,
        attribute_definition_id=volume_attr.id,
        value_number=0.5
    ))
    db.add(models.ProductAttributeValue(
        product_id=wine5.id,
        attribute_definition_id=strength_attr.id,
        value_number=15.0
    ))
    db.add(models.ProductAttributeValue(
        product_id=wine5.id,
        attribute_definition_id=glasses_per_bottle_attr.id,
        value_number=4.0
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
    
    # Add attributes for bread1
    db.add(models.ProductAttributeValue(
        product_id=bread1.id,
        attribute_definition_id=bread_weight_attr.id,
        value_number=0.4
    ))
    
    # Add attributes for tomato_paste1
    db.add(models.ProductAttributeValue(
        product_id=tomato_paste1.id,
        attribute_definition_id=paste_weight_attr.id,
        value_number=0.2
    ))
    
    # Create a wine basket as a composite product
    wine_basket = models.Product(
        product_type_id=wine_basket_type.id,
        name="Корзина из 5 вин",
        stock=5,
        unit_cost=2000.0  # This would be calculated based on components
    )
    db.add(wine_basket)
    db.commit()
    db.refresh(wine_basket)
    
    # Add components to the wine basket (5 different wines)
    db.add(models.ProductComponent(
        composite_product_id=wine_basket.id,
        component_product_id=wine1.id,
        quantity=1.0
    ))
    db.add(models.ProductComponent(
        composite_product_id=wine_basket.id,
        component_product_id=wine2.id,
        quantity=1.0
    ))
    db.add(models.ProductComponent(
        composite_product_id=wine_basket.id,
        component_product_id=wine3.id,
        quantity=1.0
    ))
    db.add(models.ProductComponent(
        composite_product_id=wine_basket.id,
        component_product_id=wine4.id,
        quantity=1.0
    ))
    db.add(models.ProductComponent(
        composite_product_id=wine_basket.id,
        component_product_id=wine5.id,
        quantity=1.0
    ))
    
    # Create a sandwich as a composite product
    sandwich = models.Product(
        product_type_id=sandwich_type.id,
        name="Бутерброд",
        stock=50,
        unit_cost=30.0  # Calculated from components
    )
    db.add(sandwich)
    db.commit()
    db.refresh(sandwich)
    
    # Add components to the sandwich (1/10 baton + 20g tomato paste)
    db.add(models.ProductComponent(
        composite_product_id=sandwich.id,
        component_product_id=bread1.id,
        quantity=0.1  # 1/10 of a baguette
    ))
    db.add(models.ProductComponent(
        composite_product_id=sandwich.id,
        component_product_id=tomato_paste1.id,
        quantity=0.02  # 20g = 0.02 kg
    ))
    
    # Create a tasting set as a composite product
    tasting_set = models.Product(
        product_type_id=tasting_set_type.id,
        name="Дегустационный набор",
        stock=10,
        unit_cost=500.0  # Calculated from components
    )
    db.add(tasting_set)
    db.commit()
    db.refresh(tasting_set)
    
    # Add components to the tasting set (5 glasses of wine + 1 sandwich)
    # Assuming each glass uses 1/6 of a bottle (based on 6 glasses per bottle)
    db.add(models.ProductComponent(
        composite_product_id=tasting_set.id,
        component_product_id=wine1.id,
        quantity=0.167  # ~1/6 of a bottle for one glass
    ))
    db.add(models.ProductComponent(
        composite_product_id=tasting_set.id,
        component_product_id=wine2.id,
        quantity=0.167
    ))
    db.add(models.ProductComponent(
        composite_product_id=tasting_set.id,
        component_product_id=wine3.id,
        quantity=0.167
    ))
    db.add(models.ProductComponent(
        composite_product_id=tasting_set.id,
        component_product_id=wine4.id,
        quantity=0.167
    ))
    db.add(models.ProductComponent(
        composite_product_id=tasting_set.id,
        component_product_id=wine5.id,
        quantity=0.167
    ))
    # Add one sandwich
    db.add(models.ProductComponent(
        composite_product_id=tasting_set.id,
        component_product_id=sandwich.id,
        quantity=1.0
    ))
    
    db.commit()
    
    print("Sample data initialized successfully!")

if __name__ == "__main__":
    db = database.SessionLocal()
    try:
        init_sample_data(db)
    finally:
        db.close()