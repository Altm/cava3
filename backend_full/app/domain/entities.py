from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class Unit:
    code: str
    description: str
    ratio_to_base: Decimal = Decimal("1")
    discrete_step: Optional[Decimal] = None


@dataclass
class ProductAttribute:
    key: str
    value: str


@dataclass
class Product:
    id: int
    name: str
    sku: str
    primary_category: str
    product_type: str
    attributes: Dict[str, str] = field(default_factory=dict)
    is_composite: bool = False
    is_active: bool = True


@dataclass
class CompositeComponent:
    product_id: int
    quantity: Decimal
    unit: str
    substitution_allowed: bool = False
    rounding: Optional[str] = None


@dataclass
class StockItem:
    product_id: int
    location_id: int
    quantity: Decimal
    unit: str


@dataclass
class SaleLine:
    product_id: int
    quantity: Decimal
    unit: str
    price: Decimal


@dataclass
class SaleEvent:
    event_id: str
    terminal_id: str
    location_id: int
    lines: List[SaleLine]
    status: str = "pending"


@dataclass
class Role:
    id: int
    name: str
    scope: str
    location_id: Optional[int]
    permissions: List[str]


@dataclass
class User:
    id: int
    username: str
    is_superuser: bool
    roles: List[Role]

