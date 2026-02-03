"""
E-commerce Models

Complete e-commerce data model supporting B2C and B2B scenarios.
"""

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Integer, Numeric, ForeignKey, Boolean, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt


# ============================================================================
# PRODUCT CATALOG
# ============================================================================

class EcomCategory(Base, HasId, HasCreatedAt):
    """Product categories for e-commerce"""
    __tablename__ = "ecom_category"
    
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ecom_category.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    # Relationships
    parent = relationship("EcomCategory", remote_side="EcomCategory.id")


class EcomProduct(Base, HasId, HasCreatedAt):
    """E-commerce product (links to inventory item)"""
    __tablename__ = "ecom_product"
    
    # Link to inventory system
    item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # FK to wms_item
    
    # E-commerce specific
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Categorization
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_category.id"), nullable=False, index=True)
    
    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)  # For showing discounts
    cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)  # For margin calculation
    
    # Inventory
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_backorder: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    low_stock_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    requires_shipping: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Media
    primary_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    images: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # Array of image URLs
    
    # SEO
    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta_keywords: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    # Attributes
    weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    weight_unit: Mapped[str] = mapped_column(String(10), default="lb", nullable=False)
    
    # Additional data
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # Custom attributes
    
    # Stats
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sales_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("EcomCategory")


class EcomProductVariant(Base, HasId, HasCreatedAt):
    """Product variants (size, color, etc.)"""
    __tablename__ = "ecom_product_variant"
    
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_product.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # FK to specific variant item
    
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Variant attributes (e.g., {"size": "Large", "color": "Blue"})
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Pricing (can override product price)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Inventory
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Media
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    product = relationship("EcomProduct")


# ============================================================================
# CUSTOMER & CART
# ============================================================================

class EcomCustomer(Base, HasId, HasCreatedAt):
    """E-commerce customer account"""
    __tablename__ = "ecom_customer"
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Business (for B2B)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Customer type
    customer_type: Mapped[str] = mapped_column(String(20), default="RETAIL", nullable=False)  # RETAIL, B2B, WHOLESALE
    customer_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # For pricing rules
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Stats
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    # Marketing
    accepts_marketing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class EcomAddress(Base, HasId, HasCreatedAt):
    """Customer addresses"""
    __tablename__ = "ecom_address"
    
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_customer.id"), nullable=False, index=True)
    
    address_type: Mapped[str] = mapped_column(String(20), nullable=False)  # BILLING, SHIPPING
    
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)  # ISO 2-letter code
    
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    customer = relationship("EcomCustomer")


class EcomCart(Base, HasId, HasCreatedAt):
    """Shopping cart"""
    __tablename__ = "ecom_cart"
    
    # Can be linked to customer or anonymous (session)
    customer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ecom_customer.id"), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)  # For anonymous users
    
    # Cart state
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, ABANDONED, CONVERTED
    
    # Totals
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    # Promotions
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    customer = relationship("EcomCustomer")


class EcomCartItem(Base, HasId, HasCreatedAt):
    """Items in shopping cart"""
    __tablename__ = "ecom_cart_item"
    
    cart_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_cart.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_product.id"), nullable=False)
    variant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ecom_product_variant.id"), nullable=True)
    
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Snapshot of product details at add-to-cart time
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_sku: Mapped[str] = mapped_column(String(64), nullable=False)
    product_image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    # Relationships
    cart = relationship("EcomCart")
    product = relationship("EcomProduct")
    variant = relationship("EcomProductVariant")


# ============================================================================
# ORDERS
# ============================================================================

class EcomOrder(Base, HasId, HasCreatedAt):
    """E-commerce order"""
    __tablename__ = "ecom_order"
    
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    
    # Customer
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_customer.id"), nullable=False, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED, REFUNDED
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False)
    # PENDING, AUTHORIZED, PAID, PARTIALLY_REFUNDED, REFUNDED, FAILED
    fulfillment_status: Mapped[str] = mapped_column(String(20), nullable=False)
    # UNFULFILLED, PARTIALLY_FULFILLED, FULFILLED
    
    # Financial
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Promotions
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    discount_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Shipping
    shipping_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    carrier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Addresses (denormalized for history)
    billing_address: Mapped[dict] = mapped_column(JSON, nullable=False)
    shipping_address: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Customer info (snapshot)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Payment
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Integration
    sales_order_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # Link to ERP sales order
    
    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    
    # Dates
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("EcomCustomer")


class EcomOrderItem(Base, HasId, HasCreatedAt):
    """Order line items"""
    __tablename__ = "ecom_order_item"
    
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_order.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)  # Snapshot, may not exist anymore
    variant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    
    # Product details (snapshot)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_sku: Mapped[str] = mapped_column(String(64), nullable=False)
    product_image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    variant_attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Pricing
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    # Fulfillment
    fulfillment_status: Mapped[str] = mapped_column(String(20), default="UNFULFILLED", nullable=False)
    quantity_fulfilled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    order = relationship("EcomOrder")


# ============================================================================
# REVIEWS & RATINGS
# ============================================================================

class EcomProductReview(Base, HasId, HasCreatedAt):
    """Product reviews and ratings"""
    __tablename__ = "ecom_product_review"
    
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_product.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_customer.id"), nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ecom_order.id"), nullable=True)  # Verified purchase
    
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 stars
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Moderation
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Helpfulness
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    product = relationship("EcomProduct")
    customer = relationship("EcomCustomer")


# ============================================================================
# PRICING & PROMOTIONS
# ============================================================================

class EcomPricingRule(Base, HasId, HasCreatedAt):
    """Pricing rules for B2B customers"""
    __tablename__ = "ecom_pricing_rule"
    
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Applicability
    customer_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ecom_customer.id"), nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ecom_product.id"), nullable=True)
    category_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ecom_category.id"), nullable=True)
    
    # Discount
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PERCENTAGE, FIXED_AMOUNT
    discount_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Conditions
    min_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Validity
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class EcomCoupon(Base, HasId, HasCreatedAt):
    """Discount coupons"""
    __tablename__ = "ecom_coupon"
    
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Discount
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PERCENTAGE, FIXED_AMOUNT, FREE_SHIPPING
    discount_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Conditions
    min_purchase_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Usage limits
    usage_limit_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_limit_per_customer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Validity
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================================
# WISHLIST
# ============================================================================

class EcomWishlist(Base, HasId, HasCreatedAt):
    """Customer wishlist"""
    __tablename__ = "ecom_wishlist"
    
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_customer.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("ecom_product.id"), nullable=False)
    variant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ecom_product_variant.id"), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    customer = relationship("EcomCustomer")
    product = relationship("EcomProduct")
    variant = relationship("EcomProductVariant")
    
    __table_args__ = (
        Index('ix_wishlist_customer_product', 'customer_id', 'product_id', unique=True),
    )


# ============================================================================
# INDEXES
# ============================================================================

Index('ix_ecom_product_active', EcomProduct.is_active, EcomProduct.created_at)
Index('ix_ecom_product_featured', EcomProduct.is_featured, EcomProduct.sort_order)
Index('ix_ecom_order_customer_status', EcomOrder.customer_id, EcomOrder.status)
Index('ix_ecom_order_date', EcomOrder.order_date.desc())
