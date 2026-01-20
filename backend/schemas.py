from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any

class UnitBase(BaseModel):
    symbol: str
    name: str
    base_unit_id: Optional[int] = None
    conversion_factor: Optional[float] = None

class Unit(UnitBase):
    id: int

    class Config:
        from_attributes = True

class AttributeDefinitionBase(BaseModel):
    name: str
    code: str
    data_type: str  # "number", "boolean", "string"
    unit_id: Optional[int] = None
    is_required: bool = False

class AttributeDefinition(AttributeDefinitionBase):
    id: int
    product_type_id: int

    class Config:
        from_attributes = True

class ProductTypeBase(BaseModel):
    name: str
    is_composite: bool = False

class ProductType(ProductTypeBase):
    id: int
    attributes: List[AttributeDefinition] = []

    class Config:
        from_attributes = True

class ProductAttributeValueCreate(BaseModel):
    attribute_definition_id: int
    value: Union[float, bool, str]

class ProductCreate(BaseModel):
    product_type_id: int
    name: str
    unit_cost: float
    stock: float = 0.0
    attributes: List[ProductAttributeValueCreate] = []
    components: List[Dict[str, float]] = []  # {component_product_id: quantity}

class ProductUpdate(ProductCreate):
    pass

class Product(BaseModel):
    id: int
    product_type_id: int
    name: str
    stock: float
    unit_cost: float
    is_composite: bool
    attributes: Dict[str, Any] = {}
    components: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class SaleRequest(BaseModel):
    product_id: int
    quantity: float