from sqlalchemy import (
    Column, Integer, String, Boolean, Float, ForeignKey, JSON, Enum, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from typing import Optional, List, Any

Base = declarative_base()

class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, nullable=False)  # л, кг, шт
    name = Column(String, nullable=False)
    base_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    conversion_factor = Column(Float, nullable=True)  # 1000 для мл → л

    base_unit = relationship("Unit", remote_side=[id])

class ProductType(Base):
    __tablename__ = "product_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    is_composite = Column(Boolean, default=False, nullable=False)

class AttributeDefinition(Base):
    __tablename__ = "attribute_definitions"
    __table_args__ = (UniqueConstraint("product_type_id", "code"),)

    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)  # volume, has_pit
    data_type = Column(Enum("number", "boolean", "string", name="data_type_enum"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    is_required = Column(Boolean, default=False)

    product_type = relationship("ProductType")
    unit = relationship("Unit")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)
    name = Column(String, nullable=False)
    stock = Column(Float, default=0.0)  # в базовой единице
    unit_cost = Column(Float, nullable=False)  # за единицу хранения

    product_type = relationship("ProductType")
    attributes = relationship("ProductAttributeValue", back_populates="product")
    components = relationship("ProductComponent", foreign_keys="[ProductComponent.composite_product_id]", back_populates="composite_product")

    @hybrid_property
    def is_composite(self) -> bool:
        return self.product_type.is_composite

class ProductAttributeValue(Base):
    __tablename__ = "product_attribute_values"

    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    attribute_definition_id = Column(Integer, ForeignKey("attribute_definitions.id"), primary_key=True)
    value_number = Column(Float, nullable=True)
    value_boolean = Column(Boolean, nullable=True)
    value_string = Column(String, nullable=True)

    product = relationship("Product", back_populates="attributes")
    attribute_definition = relationship("AttributeDefinition")

class ProductComponent(Base):
    __tablename__ = "product_components"

    composite_product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    component_product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    quantity = Column(Float, nullable=False)  # в единицах хранения компонента

    composite_product = relationship("Product", foreign_keys=[composite_product_id], back_populates="components")
    component_product = relationship("Product", foreign_keys=[component_product_id])