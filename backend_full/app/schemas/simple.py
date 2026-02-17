from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class LocationBase(BaseModel):
    id: int
    name: str
    code: str


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
    sort_order: int = 1  # Order in which the attribute should be displayed


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
    product_attribute_id: int
    value: Union[float, bool, str, Decimal]


class ProductComponentCreate(BaseModel):
    component_product_id: int
    quantity: Decimal


class ProductCreate(BaseModel):
    product_type_id: int
    name: str
    sku: Optional[str] = None
    base_cost: Decimal
    stock: Decimal = Decimal("0")
    base_unit_id: Optional[int] = Field(default=None)  # Changed from base_unit_code to base_unit_id, made optional temporarily for frontend compatibility
    attributes: List[ProductAttributeValueCreate] = []
    components: List[ProductComponentCreate] = []
    product_units: List[ProductUnitCreate] = []


class ProductUpdate(BaseModel):
    product_type_id: int
    name: str
    sku: Optional[str] = None
    base_cost: Decimal
    stock: Decimal = Decimal("0")
    base_unit_id: Optional[int] = Field(default=None)  # Changed from base_unit_code to base_unit_id, made optional temporarily for frontend compatibility
    attributes: List[ProductAttributeValueCreate] = []
    components: List[ProductComponentCreate] = []
    product_units: List[ProductUnitCreate] = []


class ProductComponentCreate(BaseModel):
    component_product_id: int
    quantity: Decimal


class ProductComponent(ProductComponentCreate):
    id: int
    parent_product_id: int
    unit_id: int
    substitution_allowed: bool = False
    rounding: Optional[str] = None

    class Config:
        from_attributes = True


class ProductComponentTreeNode(BaseModel):
    component_product_id: int
    component_name: str
    quantity: Decimal
    unit_id: int
    unit_code: Optional[str] = None
    is_composite: bool = False
    available_quantity: Decimal = Decimal("0")
    is_cycle: bool = False
    children: List["ProductComponentTreeNode"] = []


class ProductStockUnitQuantity(BaseModel):
    unit_id: int
    unit_code: str
    ratio_to_base: Decimal
    quantity: Decimal


class ProductStockLocationView(BaseModel):
    location_id: int
    location_name: str
    location_code: str
    base_quantity: Decimal
    display_quantity: str
    units: List[ProductStockUnitQuantity] = []


class Product(BaseModel):
    id: int
    product_type_id: int
    name: str
    base_cost: Decimal
    stock: Decimal
    is_composite: bool
    base_unit_id: int  # Added base_unit_id
    attributes: List[ProductAttributeValueCreate] = []
    components: List[ProductComponent] = []
    product_units: List[ProductUnit] = []

    class Config:
        from_attributes = True


class ProductMetaView(BaseModel):
    image: Optional[str] = None
    body_html: Optional[str] = None
    vendor: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[str] = None
    variant_barcode: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class ProductView(Product):
    meta: Optional[ProductMetaView] = None
    component_tree: List[ProductComponentTreeNode] = []
    stock_by_location: List[ProductStockLocationView] = []


class ProductImageOut(BaseModel):
    image: str
    image_url: str


class SaleRequest(BaseModel):
    product_id: int
    quantity: Decimal


class SaleCheckoutLineIn(BaseModel):
    kind: str = Field(..., pattern=r"^(product|item_qr|box_qr|glass)$")
    product_id: Optional[int] = None
    quantity: Optional[Decimal] = None
    unit_id: Optional[int] = None
    qr_code: Optional[str] = None
    item_qr_code: Optional[str] = None


class SaleCheckoutRequest(BaseModel):
    lines: List[SaleCheckoutLineIn] = []


class SaleCheckoutResolvedLine(BaseModel):
    kind: str
    product_id: int
    product_name: str
    quantity: Decimal
    unit_id: int
    unit_code: str
    unit_price: Decimal
    total_price: Decimal
    resolved_item_ids: List[int] = []
    resolved_box_id: Optional[int] = None


class SaleCheckoutOut(BaseModel):
    sale_id: int
    terminal_id: str
    location_id: int
    total_amount: Decimal
    lines: List[SaleCheckoutResolvedLine] = []
    register_payload: Dict[str, Any]
    register_response: Dict[str, Any]


class SaleListItemOut(BaseModel):
    id: int
    sale_id: Optional[int] = None
    event_id: str
    status: str
    terminal_id: Optional[str] = None
    location_id: int
    location_name: Optional[str] = None
    user_id: Optional[int] = None
    lines_count: int
    total_amount: Decimal
    created_at: datetime
    confirmed_at: Optional[datetime] = None


ProductComponentTreeNode.model_rebuild()
