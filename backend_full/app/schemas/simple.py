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


class PriceCalculatorOut(BaseModel):
    version_id: int
    calculator_code: str
    calculator_name: str
    calculator_version: str
    source_hash: str
    file: str
    class_name: str
    description: Optional[str] = None


class PriceRevisionCreate(BaseModel):
    location_id: int
    name: Optional[str] = None
    mode: str = Field(..., pattern=r"^(percent|fixed|calculator)$")
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    percent_delta: Optional[Decimal] = None
    amount_delta: Optional[Decimal] = None
    calculator_version_id: Optional[int] = None
    calculator_file: Optional[str] = None
    calculator_class: Optional[str] = None
    calculator_params: Dict[str, Any] = Field(default_factory=dict)


class PriceRevisionItemOut(BaseModel):
    product_id: int
    product_name: str
    unit_id: int
    unit_code: str
    currency: str
    amount: Decimal
    previous_amount: Optional[Decimal] = None
    base_price: Optional[Decimal] = None
    average_purchase_cost: Optional[Decimal] = None
    lots: List["PriceItemLotOut"] = Field(default_factory=list)


class PriceItemLotOut(BaseModel):
    lot_id: int
    supplier_lot_number: Optional[str] = None
    received_at: datetime
    purchase_price: Optional[Decimal] = None
    in_stock_items: int


class PriceRevisionListOut(BaseModel):
    id: int
    location_id: int
    location_name: Optional[str] = None
    name: Optional[str] = None
    mode: str
    currency: str
    percent_delta: Optional[Decimal] = None
    amount_delta: Optional[Decimal] = None
    calculator_version_id: Optional[int] = None
    calculator_name: Optional[str] = None
    calculator_version: Optional[str] = None
    calculator_source_hash: Optional[str] = None
    calculator_file: Optional[str] = None
    calculator_class: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    effective_from: datetime
    effective_to: Optional[datetime] = None
    items_count: int


class PriceRevisionDetailOut(BaseModel):
    id: int
    location_id: int
    location_name: Optional[str] = None
    name: Optional[str] = None
    mode: str
    currency: str
    percent_delta: Optional[Decimal] = None
    amount_delta: Optional[Decimal] = None
    calculator_version_id: Optional[int] = None
    calculator_name: Optional[str] = None
    calculator_version: Optional[str] = None
    calculator_source_hash: Optional[str] = None
    calculator_file: Optional[str] = None
    calculator_class: Optional[str] = None
    calculator_params: Dict[str, Any] = Field(default_factory=dict)
    created_by_user_id: Optional[int] = None
    created_at: datetime
    items: List[PriceRevisionItemOut] = Field(default_factory=list)


class PriceCurrentOut(BaseModel):
    location_id: int
    location_name: Optional[str] = None
    revision_id: Optional[int] = None
    revision_name: Optional[str] = None
    revision_calculator_name: Optional[str] = None
    revision_calculator_version: Optional[str] = None
    revision_calculator_source_hash: Optional[str] = None
    revision_created_at: Optional[datetime] = None
    items: List[PriceRevisionItemOut] = Field(default_factory=list)


class LotListOut(BaseModel):
    lot_id: int
    product_id: int
    product_name: str
    supplier_lot_number: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    received_at: datetime
    location_id: int
    location_name: str
    location_code: str
    in_stock_items: int


class LotItemOut(BaseModel):
    product_item_id: int
    product_item_qr_code: str
    status: str
    location_id: int
    location_name: str
    location_code: Optional[str] = None
    box_id: Optional[int] = None
    box_qr_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LotDetailOut(BaseModel):
    lot_id: int
    product_id: int
    product_name: str
    supplier_lot_number: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    received_at: datetime
    receipt_id: int
    receipt_status: str
    total_items: int
    in_stock_items: int
    items: List[LotItemOut] = Field(default_factory=list)


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


class ProductUnitUpdate(BaseModel):
    ratio_to_base: Decimal = Field(..., gt=0)
    discrete_step: Optional[Decimal] = None


class ProductUnit(ProductUnitCreate):
    id: Optional[int] = None
    product_id: int
    source: Optional[str] = None

    class Config:
        from_attributes = True


class ProductGlassLinkUpdate(BaseModel):
    bottle_unit_id: int
    glass_unit_id: int
    glasses_in_bottle: int = Field(..., gt=0)
    glass_discrete_step: Optional[Decimal] = Field(default=Decimal("1"), gt=0)


class ProductGlassLinkOut(BaseModel):
    product_id: int
    base_unit_id: int
    bottle_unit_id: int
    bottle_ratio_to_base: Decimal
    glass_unit_id: int
    glass_ratio_to_base: Decimal
    glasses_in_bottle: int
    product_units: List[ProductUnit] = []


class ProductTypeUnitCreate(BaseModel):
    unit_id: int
    ratio_to_base: Decimal = Field(..., gt=0)
    discrete_step: Optional[Decimal] = None


class ProductTypeUnit(ProductTypeUnitCreate):
    id: Optional[int] = None
    product_type_id: int

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
    strict_units_by_type: bool = False
    attributes: List[ProductAttributeCreate] = []
    product_type_units: List[ProductTypeUnitCreate] = []


class ProductTypeUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    is_composite: bool = False
    strict_units_by_type: bool = False
    attributes: List[ProductAttributeCreate] = []
    product_type_units: List[ProductTypeUnitCreate] = []


class ProductType(ProductTypeCreate):
    id: int
    attributes: List[ProductAttribute] = []
    product_type_units: List[ProductTypeUnit] = []

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
    default_portion_size: Optional[Decimal] = None
    portions_per_unit: Optional[int] = None
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
    default_portion_size: Optional[Decimal] = None
    portions_per_unit: Optional[int] = None
    stock: Decimal = Decimal("0")
    base_unit_id: Optional[int] = Field(default=None)  # Changed from base_unit_code to base_unit_id, made optional temporarily for frontend compatibility
    attributes: List[ProductAttributeValueCreate] = []
    components: List[ProductComponentCreate] = []
    product_units: List[ProductUnitCreate] = []


class ProductComponentCreate(BaseModel):
    component_product_id: int
    quantity: Decimal
    unit_id: Optional[int] = None
    substitution_allowed: bool = False
    rounding: Optional[str] = None
    waste_factor: Decimal = Decimal("0")


class ProductComponentUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    unit_id: Optional[int] = None
    substitution_allowed: Optional[bool] = None
    rounding: Optional[str] = None
    waste_factor: Optional[Decimal] = None


class ProductComponent(ProductComponentCreate):
    id: int
    parent_product_id: int
    unit_id: int
    substitution_allowed: bool = False
    rounding: Optional[str] = None
    waste_factor: Decimal = Decimal("0")

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
    default_portion_size: Optional[Decimal] = None
    portions_per_unit: Optional[int] = None
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


class SaleDetailLineOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_sku: Optional[str] = None
    quantity: Decimal
    unit_id: int
    unit_code: str
    currency: str
    line_total_amount: Decimal


class SaleDetailOut(BaseModel):
    id: int
    sale_id: Optional[int] = None
    event_id: str
    status: str
    terminal_id: Optional[str] = None
    location_id: int
    location_name: Optional[str] = None
    user_id: Optional[int] = None
    total_amount: Decimal
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    payload: Dict[str, Any]
    lines: List[SaleDetailLineOut] = []


ProductComponentTreeNode.model_rebuild()
PriceRevisionItemOut.model_rebuild()
