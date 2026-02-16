from __future__ import annotations

from typing import Optional, Literal, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field


class LabelsOut(BaseModel):
    labels: List[str]


class ReceiptCreate(BaseModel):
    to_location_id: int


class ReceiptOut(BaseModel):
    id: int
    to_location_id: int
    status: str

    class Config:
        from_attributes = True


class ReceiptListOut(BaseModel):
    id: int
    to_location_id: int
    status: str
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReceiptLineCreate(BaseModel):
    product_id: int
    qty: Decimal
    unit_id: int
    supplier_lot_number: Optional[str] = None


class ReceiptLineOut(BaseModel):
    id: int
    receipt_id: int
    product_id: int
    qty: Decimal
    unit_id: int
    supplier_lot_number: Optional[str] = None

    class Config:
        from_attributes = True


class ReceiptGenerateOut(BaseModel):
    receipt_id: int
    lots_created: int
    items_created: int


class BoxCreate(BaseModel):
    product_id: int
    lot_id: int
    location_id: int
    sealed: bool = True


class BoxOut(BaseModel):
    id: int
    uuid: UUID
    qr_code: str
    product_id: int
    lot_id: int
    location_id: int
    sealed: bool
    status: str

    class Config:
        from_attributes = True


class BoxListOut(BaseModel):
    id: int
    uuid: UUID
    qr_code: str
    product_id: int
    lot_id: int
    location_id: int
    sealed: bool
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BoxAddItem(BaseModel):
    qr_code: str


class TransferCreate(BaseModel):
    from_location_id: int
    to_location_id: int


class TransferDocOut(BaseModel):
    id: int
    from_location_id: int
    to_location_id: int
    status: str

    class Config:
        from_attributes = True


class TransferDocDetailOut(BaseModel):
    id: int
    from_location_id: int
    to_location_id: int
    status: str
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    planned_count: int = 0
    picked_count: int = 0
    received_count: int = 0
    removed_count: int = 0
    transfer_lines: List["TransferPlanLineOut"] = Field(default_factory=list)


class TransferPlanLineOut(BaseModel):
    transfer_line_id: int
    product_id: int
    product_name: str
    qty_base: int
    pick_policy: str
    planned_qr_codes: List[str] = Field(default_factory=list)


class TransferDocListOut(BaseModel):
    id: int
    from_location_id: int
    to_location_id: int
    status: str
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransferPlan(BaseModel):
    product_id: int
    qty_base: int = Field(..., ge=1)


class TransferPlanOut(BaseModel):
    transfer_doc_id: int
    transfer_line_id: int
    planned_items: int


class TransferRemoveItem(BaseModel):
    product_item_id: int


class TransferScan(BaseModel):
    qr_code: str
    mode: Literal["picking", "receiving"]


class InventoryCreate(BaseModel):
    location_id: int


class InventoryDocOut(BaseModel):
    id: int
    location_id: int
    status: str

    class Config:
        from_attributes = True


class InventoryDocDetailOut(BaseModel):
    id: int
    location_id: int
    status: str
    created_by_user_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    expected_count: int = 0
    scanned_count: int = 0
    missing_count: int = 0
    unexpected_count: int = 0


class InventoryDocListOut(BaseModel):
    id: int
    location_id: int
    status: str
    created_by_user_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryScan(BaseModel):
    qr_code: str


class ProductItemListOut(BaseModel):
    id: int
    uuid: UUID
    qr_code: str
    product_id: int
    lot_id: int
    location_id: int
    box_id: Optional[int] = None
    status: str
    reserved_transfer_doc_id: Optional[int] = None
    lost_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanOut(BaseModel):
    kind: Literal["ITM", "BOX"]
    found: bool
    uuid: UUID

    id: Optional[int] = None
    status: Optional[str] = None
    location_id: Optional[int] = None

    # ITM specific
    product_id: Optional[int] = None
    box_id: Optional[int] = None
    reserved_transfer_doc_id: Optional[int] = None

    # BOX specific
    lot_id: Optional[int] = None
    sealed: Optional[bool] = None
