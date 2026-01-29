from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from pydantic import BaseModel


class LocationBase(BaseModel):
    id: int
    name: str
    kind: str


class Location(LocationBase):
    pass

    class Config:
        from_attributes = True



class UnitCreate(BaseModel):
    symbol: str
    name: str
    base_unit_code: Optional[str] = None
    conversion_factor: Optional[Decimal] = None


class UnitConversionSchema(BaseModel):
    id: int
    from_unit: str
    to_unit: str
    ratio: Decimal

    class Config:
        from_attributes = True


class Unit(UnitCreate):
    code: str

    class Config:
        from_attributes = True


class AttributeDefinitionCreate(BaseModel):
    product_type_id: int
    name: str
    code: str
    data_type: str  # number/boolean/string
    unit_code: Optional[str] = None
    is_required: bool = False


class AttributeDefinition(AttributeDefinitionCreate):
    id: int

    class Config:
        from_attributes = True


class ProductTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_composite: bool = False
    attributes: List[AttributeDefinitionCreate] = []


class ProductTypeUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    is_composite: bool = False
    attributes: List[AttributeDefinitionCreate] = []


class ProductType(ProductTypeCreate):
    id: int
    attributes: List[AttributeDefinition] = []

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
    base_unit_code: Optional[str] = None
    attributes: List[ProductAttributeValueCreate] = []
    components: List[ProductComponentCreate] = []


class ProductUpdate(BaseModel):
    product_type_id: int
    name: str
    sku: Optional[str] = None
    unit_cost: Decimal
    stock: Decimal = Decimal("0")
    base_unit_code: Optional[str] = None
    attributes: List[ProductAttributeValueCreate] = []
    components: List[ProductComponentCreate] = []


class Product(BaseModel):
    id: int
    product_type_id: int
    name: str
    unit_cost: Decimal
    stock: Decimal
    is_composite: bool
    #stock_by_location: Optional[Decimal] = None  # ← для фильтрации по location_id
    #locations: List[Location] = []  # ← все локации, где есть продукт
    attributes: List[ProductAttributeValueCreate] = []
    components: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class SaleRequest(BaseModel):
    product_id: int
    quantity: Decimal
