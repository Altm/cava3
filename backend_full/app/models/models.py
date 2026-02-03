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
    select,
    func,
    event
)
from sqlalchemy.orm import Mapped, mapped_column, column_property, relationship
from app.infrastructure.db.base import Base
from app.common.decorators import deprecated

class Unit(Base):
    """Units of measure with type classification."""

    __tablename__ = 'unit'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="Human-readable code (bottle, box, glass)")
    description: Mapped[str] = mapped_column(String(255), nullable=False, comment="Description of the unit")
    unit_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="Type: 'base', 'package', 'portion'")
    is_discrete: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Discreteness flag")

    # Relationships
    product_units: Mapped[list["ProductUnit"]] = relationship(back_populates="unit", cascade="all, delete-orphan")
    stocks: Mapped[list["Stock"]] = relationship(back_populates="unit")
    price_lists: Mapped[list["PriceList"]] = relationship(back_populates="unit")
    adjustments: Mapped[list["Adjustment"]] = relationship(back_populates="unit")
    transfers: Mapped[list["Transfer"]] = relationship(back_populates="unit")
    sale_lines: Mapped[list["SaleLine"]] = relationship(back_populates="unit")
    attribute_definitions: Mapped[list["ProductAttribute"]] = relationship(back_populates="unit")
    composite_components: Mapped[list["CompositeComponent"]] = relationship(back_populates="unit")


class ProductUnit(Base):
    """Product-specific unit configurations with conversion ratios."""

    __tablename__ = 'product_unit'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id", ondelete="RESTRICT"), nullable=False)
    ratio_to_base: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), nullable=False, comment="Ratio relative to product's base unit")
    discrete_step: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 6), nullable=True, comment="Step for fractional quantities")

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="product_units")
    unit: Mapped["Unit"] = relationship("Unit", back_populates="product_units")

    __table_args__ = (
        UniqueConstraint("product_id", "unit_id", name="uq_product_unit_product_unit"),
        CheckConstraint("ratio_to_base > 0", name="ck_product_unit_positive_ratio"),
    )



class Stock(Base):
    """Stock balances by location and product."""

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Location reference")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), default=Decimal("0"), comment="Available quantity")
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), comment="Unit in which quantity is stored")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Last update timestamp")
    
    # Связи
    location = relationship("Location", back_populates="stocks")
    product = relationship("Product", back_populates="stocks")
    unit: Mapped["Unit"] = relationship("Unit", back_populates="stocks")
    
    __table_args__ = (
        UniqueConstraint("location_id", "product_id", name="uq_stock_location_product"),
        CheckConstraint("quantity >= 0", name="ck_stock_non_negative"),
    )


class ProductType(Base):
    """Types of products (wine, olive, etc)."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, comment="Type name")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Extended description")
    is_composite: Mapped[bool] = mapped_column(Boolean, default=False, comment="Composite flag for recipes")

    # Relationships
    attributes: Mapped[list["ProductAttribute"]] = relationship(back_populates="product_type")


class Product(Base):
    """Base product representation."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), comment="Display name")
    sku: Mapped[str] = mapped_column(String(64), unique=True, comment="SKU code")
    primary_category: Mapped[str] = mapped_column(String(64), comment="Primary category tag")
    product_type_id: Mapped[int] = mapped_column(ForeignKey("product_type.id"), comment="Product type reference")
    base_unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), comment="Base unit for stock keeping")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="Soft delete flag")
    #unit_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=Decimal("0.00"), comment="Unit cost for catalog")
    tax_flags: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="Tax or regulatory flags")
    unit_cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True, comment="Cost per unit")
    
    product_type: Mapped["ProductType"] = relationship()
    attributes: Mapped[list["ProductAttributeValue"]] = relationship(back_populates="product")
    components: Mapped[list["CompositeComponent"]] = relationship(
        foreign_keys="[CompositeComponent.parent_product_id]",
        back_populates="parent_product"
    )
    
    # New relationships for the updated schema
    product_units: Mapped[list["ProductUnit"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    stocks = relationship("Stock", back_populates="product")

    @property
    def is_composite(self) -> bool:
        """Return is_composite from associated product type"""
        return self.product_type.is_composite if self.product_type else False


class ProductCategory(Base):
    """Secondary categories for a product."""

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    category: Mapped[str] = mapped_column(String(64), comment="Category tag")
    __table_args__ = (UniqueConstraint("product_id", "category", name="uq_product_category"),)


@deprecated(
    reason="Use ProductAttribute",
    version="0.1.0",
    alternative="ProductAttribute",
    category=FutureWarning  # Для видимости у конечных пользователей библиотеки
)
class ProductAttributeOld(Base):
    """Flexible attributes for products (deprecated)."""

    __tablename__ = 'product_attribute_old'  # Give it a different table name

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    name: Mapped[str] = mapped_column(String(64), comment="Attribute name")
    value: Mapped[str] = mapped_column(String(255), comment="Attribute value")
    __table_args__ = (UniqueConstraint("product_id", "name", name="uq_product_attribute_old"),)


class ProductAttribute(Base):
    """Attribute definitions bound to product types with explicit data types (previously called AttributeDefinition)."""

    __tablename__ = 'product_attribute'

    id: Mapped[int] = mapped_column(primary_key=True)
    product_type_id: Mapped[int] = mapped_column(ForeignKey("product_type.id"), comment="Product type reference")
    name: Mapped[str] = mapped_column(String(128), comment="Display name")
    code: Mapped[str] = mapped_column(String(64), comment="Machine code")
    data_type: Mapped[str] = mapped_column(String(16), comment="number/boolean/string")
    unit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("unit.id"), nullable=True, comment="Optional unit reference")
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, comment="Is attribute required")
    sort_order: Mapped[int] = mapped_column(Integer, default=1, comment="Order in which the attribute should be displayed")
    __table_args__ = (UniqueConstraint("product_type_id", "code", name="uq_productattr_producttype_code"),)

    # Relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="attribute_definitions")
    product_type: Mapped["ProductType"] = relationship("ProductType", back_populates="attributes")




class ProductAttributeValue(Base):
    """Typed values for attributes per product."""

    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), primary_key=True, comment="Product reference")
    product_attribute_id: Mapped[int] = mapped_column(ForeignKey("product_attribute.id"), primary_key=True, comment="Product attribute reference")
    value_number: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True, comment="Numeric value")
    value_boolean: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, comment="Boolean value")
    value_string: Mapped[Optional[str]] = mapped_column(String(3000), nullable=True, comment="String value")
    __table_args__ = (UniqueConstraint("product_id", "product_attribute_id", name="uq_product_attr_val_prod_attr"),)
    product: Mapped["Product"] = relationship("Product", back_populates="attributes")
    product_attribute: Mapped["ProductAttribute"] = relationship("ProductAttribute")




class CompositeComponent(Base):
    """Components for composite or recipe products."""

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Composite parent product")
    component_product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Component product")
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), comment="Quantity of component")
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), comment="Unit for component quantity")
    substitution_allowed: Mapped[bool] = mapped_column(Boolean, default=False, comment="If substitutions allowed")
    rounding: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="Rounding rule identifier")
    __table_args__ = (
        UniqueConstraint("parent_product_id", "component_product_id", name="uq_component_unique"),
    )
    parent_product: Mapped["Product"] = relationship(
        "Product",
        foreign_keys=[parent_product_id],
        back_populates="components"
    )
    component_product: Mapped["Product"] = relationship(
        "Product",
        foreign_keys=[component_product_id]
    )
    unit: Mapped["Unit"] = relationship("Unit", back_populates="composite_components")


class Location(Base):
    """Physical or logical locations holding stock."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, comment="Location name")
    kind: Mapped[str] = mapped_column(String(64), comment="Type of location e.g. warehouse, bar")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="Soft delete flag")
    # Связь с запасами
    stocks = relationship("Stock", back_populates="location")


class PriceList(Base):
    """Prices per location and product."""

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Location reference")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), comment="Unit for pricing")
    currency: Mapped[str] = mapped_column(String(3), default="USD", comment="Currency code")
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), comment="Price amount")
    __table_args__ = (
        UniqueConstraint("location_id", "product_id", "unit_id", name="uq_price_location_product_unit"),
    )

    # Relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="price_lists")


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
    sale_event_id: Mapped[int] = mapped_column(ForeignKey("sale_event.id"), comment="Sale event reference")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Sold product id")
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), comment="Quantity sold in given unit")
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), comment="Unit id for quantity")
    currency: Mapped[str] = mapped_column(String(3), default="USD", comment="Currency code")
    price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), comment="Extended price for this line")

    # Relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="sale_lines")


class Adjustment(Base):
    """Manual stock adjustments for corrections."""

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Location reference")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    delta: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), comment="Adjustment amount")
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), comment="Unit id for delta")
    reason: Mapped[str] = mapped_column(String(255), comment="Reason for adjustment")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Created timestamp")

    # Relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="adjustments")


class Transfer(Base):
    """Stock transfer between locations."""

    id: Mapped[int] = mapped_column(primary_key=True)
    from_location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Source location")
    to_location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), comment="Destination location")
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), comment="Product reference")
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), comment="Transferred quantity")
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), comment="Unit used")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="Created timestamp")

    # Relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="transfers")


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