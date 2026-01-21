from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union


class UnitBase(BaseModel):
    code: str
    description: str
    ratio_to_base: Optional[float] = 1.0
    discrete_step: Optional[float] = None


class Unit(UnitBase):
    code: str

    class Config:
        from_attributes = True


class AttributeDefinitionBase(BaseModel):
    name: str
    code: str
    data_type: str  # "number", "boolean", "string"
    unit_id: Optional[str] = None
    is_required: bool = False
    product_type_id: int


class AttributeDefinition(AttributeDefinitionBase):
    id: int

    class Config:
        from_attributes = True


class ProductTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
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
    name: str
    sku: str
    primary_category: str
    product_type_id: int
    base_unit_code: str
    is_composite: Optional[bool] = False
    is_active: Optional[bool] = True
    tax_flags: Optional[str] = None
    unit_cost: Optional[float] = None
    attributes: List[ProductAttributeValueCreate] = []
    components: List[Dict[str, Any]] = []  # {component_product_id: quantity}


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    primary_category: Optional[str] = None
    product_type_id: Optional[int] = None
    base_unit_code: Optional[str] = None
    is_composite: Optional[bool] = None
    is_active: Optional[bool] = None
    tax_flags: Optional[str] = None
    unit_cost: Optional[float] = None
    attributes: List[ProductAttributeValueCreate] = []
    components: List[Dict[str, Any]] = []


class Product(BaseModel):
    id: int
    name: str
    sku: str
    primary_category: str
    product_type_id: int
    base_unit_code: str
    is_composite: bool
    is_active: bool
    tax_flags: Optional[str] = None
    unit_cost: Optional[float] = None
    attributes: Dict[str, Any] = {}
    components: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class SaleRequest(BaseModel):
    product_id: int
    quantity: float