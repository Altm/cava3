from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RawProductCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_type_id: int
    name: str = Field(..., min_length=1, max_length=255)
    sku: Optional[str] = Field(default=None, max_length=100)
    primary_category: str = Field(..., min_length=1, max_length=255)
    base_unit_id: int
    base_cost: Decimal
    default_portion_size: Optional[Decimal] = None
    portions_per_unit: Optional[int] = None
    is_active: bool = True


class RawProductUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_type_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    sku: Optional[str] = Field(default=None, max_length=100)
    primary_category: Optional[str] = Field(default=None, min_length=1, max_length=255)
    base_unit_id: Optional[int] = None
    base_cost: Optional[Decimal] = None
    default_portion_size: Optional[Decimal] = None
    portions_per_unit: Optional[int] = None
    is_active: Optional[bool] = None


class StockAdjustIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_id: int
    product_id: int
    quantity: Decimal
    unit_id: int
