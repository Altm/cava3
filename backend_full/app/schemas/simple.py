from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from pydantic import BaseModel, Field


class LocationBase(BaseModel):
    id: int
    name: str
    kind: str


class Location(LocationBase):
    pass

    class Config:
        from_attributes = True


class UnitBase(BaseModel):
    code: str
    description: str
    unit_type: str = Field(..., pattern=r"^(base|package|portion)$")  # 'base', 'package', 'portion'
    is_discrete: bool = True


class UnitCreate(UnitBase):
    pass


class Unit(UnitBase):
    id: int

    class Config:
        from_attributes = True


class UnitUpdate(UnitBase):
    code: str
    description: str
    unit_type: str = Field(..., pattern=r"^(base|package|portion)$")  # 'base', 'package', 'portion'
    is_discrete: bool = True


class ProductUnitCreate(BaseModel):
    unit_id: int
    ratio_to_base: Decimal = Field(..., gt=0)  # Greater than 0
    discrete_step: Optional[Decimal] = None


class ProductUnit(ProductUnitCreate):
    id: int
    product_id: int

    class Config:
        from_attributes = True


class UnitConversionSchema(BaseModel):
    id: int
    from_unit: str
    to_unit: str
    ratio: Decimal

    class Config:
        from_attributes = True


class ProductAttributeCreate(BaseModel):
    product_type_id: int
    name: str
    code: str
    data_type: str  # number/boolean/string
    unit_id: Optional[int] = None  # Changed from unit_code to unit_id
    is_required: bool = False


class ProductAttribute(ProductAttributeCreate):
    id: int

    class Config:
        from_attributes = True


class ProductTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_composite: bool = False
    attributes: List[ProductAttributeCreate] = []


class ProductTypeUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    is_composite: bool = False
    attributes: List[ProductAttributeCreate] = []


class ProductType(ProductTypeCreate):
    id: int
    attributes: List[ProductAttribute] = []

    class Config:
        from_attributes = True


class ProductAttributeValueCreate(BaseModel):
    attribute_definition_id: int
    value: Union[float, bool, str, Decimal]


class ProductComponentCreate(BaseModel):
    component_product_id: int
    quantity: Decimal


class ProductCreate(BaseModel):
    product_type_id: int
    name: str
    sku: Optional[str] = None
    unit_cost: Decimal
    stock: Decimal = Decimal("0")
    base_unit_id: Optional[int] = Field(default=None)  # Changed from base_unit_code to base_unit_id, made optional temporarily for frontend compatibility
    attributes: List[ProductAttributeValueCreate] = []
    components: List[ProductComponentCreate] = []


class ProductUpdate(BaseModel):
    product_type_id: int
    name: str
    sku: Optional[str] = None
    unit_cost: Decimal
    stock: Decimal = Decimal("0")
    base_unit_id: Optional[int] = Field(default=None)  # Changed from base_unit_code to base_unit_id, made optional temporarily for frontend compatibility
    attributes: List[ProductAttributeValueCreate] = []
    components: List[ProductComponentCreate] = []


class Product(BaseModel):
    id: int
    product_type_id: int
    name: str
    unit_cost: Decimal
    stock: Decimal
    is_composite: bool
    base_unit_id: int  # Added base_unit_id
    attributes: List[ProductAttributeValueCreate] = []
    components: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class SaleRequest(BaseModel):
    product_id: int
    quantity: Decimal