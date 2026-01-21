from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    DECIMAL,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.db.base import Base


class Unit(Base):
    """Units of measure with conversion hints."""

    code: Mapped[str] = mapped_column(String(32), primary_key=True, comment="Unit code, e.g. bottle, glass")
    description: Mapped[str] = mapped_column(String(255), comment="Human readable description")
    ratio_to_base: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 6), default=Decimal("1"), comment="Conversion ratio to base unit for this product group"
    )
    discrete_step: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 6), nullable=True, comment="Optional discrete step to control fractional quantities"
    )


class UnitConversion(Base):
    """Explicit conversion table between units."""

    id: Mapped[int] = mapped_column(primary_key=True)
    from_unit: Mapped[str] = mapped_column(ForeignKey("unit.code"), comment="Source unit")
    to_unit: Mapped[str] = mapped_column(ForeignKey("unit.code"), comment="Destination unit")
    ratio: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), comment="Multiply by ratio to convert from source to dest")
    __table_args__ = (UniqueConstraint("from_unit", "to_unit", name="uq_unit_conversion"),)


class ProductType(Base):
    """Types of products (wine, olive, etc)."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, comment="Type name")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Extended description")


class Product(Base):
    """Base product representation."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), comment="Display name")
    sku: Mapped[str] = mapped_column(String(64), unique=True, comment="SKU code")
    primary_category: Mapped[str] = mapped_column(String(64), comment="Primary category tag")
    product_type_id: Mapped[int] = mapped_column(ForeignKey("producttype.id"), comment="Product type reference")
    base_unit_code: Mapped[str] = mapped_column(ForeignKey("unit.code"), comment="Base unit for stock keeping")
    is_composite: Mapped[bool] = mapped_column(Boolean, default=False, comment="Indicates composite product")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="Soft delete flag")
    tax_flags: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="Tax or regulatory flags")
    product_type: Mapped["ProductType"] = relationship()


class ProductCategory(Base):
    """Secondary categories for a product."""

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    category: Mapped[str] = mapped_column(String(64), comment="Category tag")
    __table_args__ = (UniqueConstraint("product_id", "category", name="uq_product_category"),)


class ProductAttribute(Base):
    """Flexible attributes for products."""

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    name: Mapped[str] = mapped_column(String(64), comment="Attribute name")
    value: Mapped[str] = mapped_column(String(255), comment="Attribute value")
    __table_args__ = (UniqueConstraint("product_id", "name", name="uq_product_attribute"),)


class CompositeComponent(Base):
    """Components for composite or recipe products."""

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Composite parent product")
    component_product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Component product")
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), comment="Quantity of component")
    unit_code: Mapped[str] = mapped_column(ForeignKey("unit.code"), comment="Unit for component quantity")
    substitution_allowed: Mapped[bool] = mapped_column(Boolean, default=False, comment="If substitutions allowed")
    rounding: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="Rounding rule identifier")
    __table_args__ = (
        UniqueConstraint("parent_product_id", "component_product_id", name="uq_component_unique"),
    )


class Location(Base):
    """Physical or logical locations holding stock."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, comment="Location name")
    kind: Mapped[str] = mapped_column(String(64), comment="Type of location e.g. warehouse, bar")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="Soft delete flag")


class Stock(Base):
    """Stock balances by location and product."""

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Location reference")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), default=Decimal("0"), comment="Available quantity")
    unit_code: Mapped[str] = mapped_column(ForeignKey("unit.code"), comment="Unit in which quantity is stored")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Last update timestamp")
    __table_args__ = (
        UniqueConstraint("location_id", "product_id", name="uq_stock_location_product"),
        CheckConstraint("quantity >= 0", name="ck_stock_non_negative"),
    )


class PriceList(Base):
    """Prices per location and product."""

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Location reference")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    unit_code: Mapped[str] = mapped_column(ForeignKey("unit.code"), comment="Unit for pricing")
    currency: Mapped[str] = mapped_column(String(3), default="USD", comment="Currency code")
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), comment="Price amount")
    __table_args__ = (
        UniqueConstraint("location_id", "product_id", "unit_code", name="uq_price_location_product_unit"),
    )


class Terminal(Base):
    """Terminals allowed to send sales events."""

    id: Mapped[int] = mapped_column(primary_key=True)
    terminal_id: Mapped[str] = mapped_column(String(64), unique=True, comment="Public terminal identifier")
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Attached location")
    secret_hash: Mapped[str] = mapped_column(String(255), comment="Hash of terminal secret for HMAC validation")
    status: Mapped[str] = mapped_column(String(32), default="active", comment="Current status")


class SaleEvent(Base):
    """Sale event sent by terminal."""

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, comment="Idempotency key for sales")
    terminal_id: Mapped[int] = mapped_column(ForeignKey("terminal.id"), comment="Terminal reference")
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Location reference")
    payload: Mapped[dict] = mapped_column(JSON, comment="Original payload for audit")
    status: Mapped[str] = mapped_column(String(16), default="pending", comment="pending/confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Creation time")
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="Confirmation time")


class SaleLine(Base):
    """Normalized sale line items for analytics."""

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_event_id: Mapped[int] = mapped_column(ForeignKey("saleevent.id"), comment="Sale event reference")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Sold product id")
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), comment="Quantity sold in given unit")
    unit_code: Mapped[str] = mapped_column(ForeignKey("unit.code"), comment="Unit code for quantity")
    currency: Mapped[str] = mapped_column(String(3), default="USD", comment="Currency code")
    price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), comment="Extended price for this line")


class Adjustment(Base):
    """Manual stock adjustments for corrections."""

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Location reference")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    delta: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), comment="Adjustment amount")
    unit_code: Mapped[str] = mapped_column(ForeignKey("unit.code"), comment="Unit code for delta")
    reason: Mapped[str] = mapped_column(String(255), comment="Reason for adjustment")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Created timestamp")


class Transfer(Base):
    """Stock transfer between locations."""

    id: Mapped[int] = mapped_column(primary_key=True)
    from_location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Source location")
    to_location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Destination location")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), comment="Transferred quantity")
    unit_code: Mapped[str] = mapped_column(ForeignKey("unit.code"), comment="Unit used")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Created timestamp")


class InventorySnapshot(Base):
    """Inventory snapshot for audits."""

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Location reference")
    taken_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Snapshot time")
    data: Mapped[dict] = mapped_column(JSON, comment="Serialized snapshot data")


class User(Base):
    """System user."""

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, comment="Login name")
    password_hash: Mapped[str] = mapped_column(String(255), comment="Hash of password")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="Active flag")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, comment="Bypass RBAC flag")


class Role(Base):
    """RBAC roles with optional location scope."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, comment="Role name")
    scope: Mapped[str] = mapped_column(String(16), default="global", comment="Scope: global or location")
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("location.id"), nullable=True, comment="Optional scope location")


class Permission(Base):
    """Atomic permission strings resource.action."""

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, comment="Permission code")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Human description")


class RolePermission(Base):
    """Bridge between roles and permissions."""

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), comment="Role reference")
    permission_id: Mapped[int] = mapped_column(ForeignKey("permission.id"), comment="Permission reference")
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)


class UserRole(Base):
    """User to role mapping."""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), comment="User reference")
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), comment="Role reference")
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)


class AuditLog(Base):
    """Audit records for data changes."""

    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(128), comment="Model/table name")
    record_id: Mapped[str] = mapped_column(String(128), comment="Primary key value")
    action: Mapped[str] = mapped_column(String(16), comment="Action type insert/update/delete")
    old_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="Previous values")
    new_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="New values")
    actor: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="User or terminal id")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Creation time")


class RequestLog(Base):
    """HTTP request logs."""

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), comment="Correlation id")
    method: Mapped[str] = mapped_column(String(8), comment="HTTP method")
    path: Mapped[str] = mapped_column(String(255), comment="Request path")
    status_code: Mapped[int] = mapped_column(Integer, comment="Response status")
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), nullable=True, comment="User id if known")
    terminal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("terminal.id"), nullable=True, comment="Terminal id if known")
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="Captured context")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Log time")
