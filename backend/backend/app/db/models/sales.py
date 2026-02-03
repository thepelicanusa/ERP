"""
MODULE: SALES & ORDER MANAGEMENT
Complete sales order processing, quotes, customers, and order fulfillment
"""

from __future__ import annotations

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Integer, Numeric, ForeignKey, JSON, Boolean, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

# ============= CUSTOMER MANAGEMENT =============

class Customer(Base, HasId, HasCreatedAt):
    """Customer master - extends AR customer"""
    __tablename__ = "sales_customer"
    
    # Basic Info
    customer_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    customer_type: Mapped[str] = mapped_column(String(32), default="RETAIL", nullable=False)
    # RETAIL|WHOLESALE|DISTRIBUTOR|OEM|DIRECT
    
    # Classification
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    segment: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SMB|ENTERPRISE|GOVERNMENT
    priority: Mapped[str] = mapped_column(String(16), default="NORMAL", nullable=False)  # VIP|HIGH|NORMAL|LOW
    
    # Contact
    primary_contact: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    website: Mapped[str | None] = mapped_column(String(256), nullable=True)
    
    # Billing Address
    billing_address_line1: Mapped[str | None] = mapped_column(String(256), nullable=True)
    billing_address_line2: Mapped[str | None] = mapped_column(String(256), nullable=True)
    billing_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    billing_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    billing_postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    billing_country: Mapped[str] = mapped_column(String(3), default="USA", nullable=False)
    
    # Shipping Address
    shipping_address_line1: Mapped[str | None] = mapped_column(String(256), nullable=True)
    shipping_address_line2: Mapped[str | None] = mapped_column(String(256), nullable=True)
    shipping_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    shipping_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shipping_postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    shipping_country: Mapped[str] = mapped_column(String(3), default="USA", nullable=False)
    
    # Commercial Terms
    payment_terms: Mapped[str] = mapped_column(String(64), default="NET30", nullable=False)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    credit_status: Mapped[str] = mapped_column(String(16), default="APPROVED", nullable=False)
    # APPROVED|ON_HOLD|CREDIT_CHECK|BLOCKED
    
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    price_list_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Tax
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tax_exempt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tax_exemption_cert: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    # Sales Team
    sales_rep_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sales_territory: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_manager_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Shipping Preferences
    preferred_carrier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shipping_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shipping_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Integration
    crm_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ar_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ecommerce_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    # ACTIVE|INACTIVE|PROSPECT|BLOCKED
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


# ============= SALES QUOTES =============

class SalesQuote(Base, HasId, HasCreatedAt):
    """Sales quotation"""
    __tablename__ = "sales_quote"
    
    quote_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Customer
    customer_id: Mapped[str] = mapped_column(ForeignKey("sales_customer.id"), nullable=False, index=True)
    customer_contact: Mapped[str | None] = mapped_column(String(256), nullable=True)
    
    # Version Control
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_quote_id: Mapped[str | None] = mapped_column(ForeignKey("sales_quote.id"), nullable=True)
    
    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Terms
    payment_terms: Mapped[str] = mapped_column(String(64), nullable=False)
    shipping_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Status & Workflow
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)
    # DRAFT|PENDING_APPROVAL|SENT|ACCEPTED|REJECTED|EXPIRED|CONVERTED
    
    sent_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    response_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Sales Team
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    sales_rep_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Win/Loss
    win_probability: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)  # AI prediction
    competitor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    loss_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    
    # Conversion
    converted_to_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    conversion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_and_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    customer: Mapped[Customer] = relationship()
    parent_quote: Mapped[Optional["SalesQuote"]] = relationship(remote_side="SalesQuote.id")



class SalesQuoteLine(Base, HasId, HasCreatedAt):
    """Quote line items"""
    __tablename__ = "sales_quote_line"
    
    quote_id: Mapped[str] = mapped_column(ForeignKey("sales_quote.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Item
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Quantity & Price
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    list_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Cost (internal)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    margin_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Lead Time
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Tax
    taxable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tax_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    quote: Mapped[SalesQuote] = relationship()


# ============= SALES ORDERS =============

class SalesOrder(Base, HasId, HasCreatedAt):
    """Sales order master"""
    __tablename__ = "sales_order"
    
    order_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Customer
    customer_id: Mapped[str] = mapped_column(ForeignKey("sales_customer.id"), nullable=False, index=True)
    customer_po: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    customer_contact: Mapped[str | None] = mapped_column(String(256), nullable=True)
    
    # Addresses (can override customer default)
    ship_to_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ship_to_address_line1: Mapped[str] = mapped_column(String(256), nullable=False)
    ship_to_address_line2: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ship_to_city: Mapped[str] = mapped_column(String(128), nullable=False)
    ship_to_state: Mapped[str] = mapped_column(String(64), nullable=False)
    ship_to_postal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    ship_to_country: Mapped[str] = mapped_column(String(3), default="USA", nullable=False)
    
    bill_to_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bill_to_address_line1: Mapped[str] = mapped_column(String(256), nullable=False)
    bill_to_address_line2: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bill_to_city: Mapped[str] = mapped_column(String(128), nullable=False)
    bill_to_state: Mapped[str] = mapped_column(String(64), nullable=False)
    bill_to_postal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    bill_to_country: Mapped[str] = mapped_column(String(3), default="USA", nullable=False)
    
    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Terms
    payment_terms: Mapped[str] = mapped_column(String(64), nullable=False)
    shipping_method: Mapped[str] = mapped_column(String(64), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    carrier_service: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Dates
    requested_ship_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    promised_ship_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_ship_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Priority
    priority: Mapped[str] = mapped_column(String(16), default="NORMAL", nullable=False)
    # RUSH|HIGH|NORMAL|LOW
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    # PENDING|CONFIRMED|IN_PRODUCTION|PICKING|PACKING|SHIPPED|DELIVERED|CANCELLED|ON_HOLD
    
    hold_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    
    # Fulfillment Status
    allocation_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    # PENDING|ALLOCATED|PARTIAL|BACKORDERED
    
    picking_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    # PENDING|IN_PROGRESS|COMPLETED|SHORT_PICKED
    
    packing_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    shipping_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    
    # Invoicing
    invoice_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    # PENDING|INVOICED|PARTIAL|PAID
    
    # Sales Team
    sales_rep_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entered_by: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Source
    source_type: Mapped[str] = mapped_column(String(32), default="MANUAL", nullable=False)
    # MANUAL|ECOMMERCE|EDI|API|QUOTE_CONVERSION
    
    quote_id: Mapped[str | None] = mapped_column(ForeignKey("sales_quote.id"), nullable=True)
    ecommerce_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # WMS Integration
    wms_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    wave_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    customer: Mapped[Customer] = relationship()
    quote: Mapped[SalesQuote | None] = relationship()


class SalesOrderLine(Base, HasId, HasCreatedAt):
    """Sales order line items"""
    __tablename__ = "sales_order_line"
    
    order_id: Mapped[str] = mapped_column(ForeignKey("sales_order.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Item
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Quantity
    quantity_ordered: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_allocated: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    quantity_picked: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    quantity_shipped: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    quantity_cancelled: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    quantity_backordered: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Tax
    taxable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tax_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    # Dates
    requested_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    promised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    shipped_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Status
    line_status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)
    # OPEN|ALLOCATED|PICKING|PICKED|SHIPPED|BACKORDERED|CANCELLED
    
    # Fulfillment
    allocation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pick_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shipment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Configuration (for configurable products)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    order: Mapped[SalesOrder] = relationship()


# ============= SHIPMENTS =============

class Shipment(Base, HasId, HasCreatedAt):
    """Shipment tracking"""
    __tablename__ = "sales_shipment"
    
    shipment_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    shipment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Order
    order_id: Mapped[str] = mapped_column(ForeignKey("sales_order.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("sales_customer.id"), nullable=False, index=True)
    
    # Carrier
    carrier: Mapped[str] = mapped_column(String(64), nullable=False)
    carrier_service: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    
    # Packaging
    num_packages: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    weight_uom: Mapped[str] = mapped_column(String(8), default="LBS", nullable=False)
    
    # Costs
    freight_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    freight_charged_to_customer: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    # PENDING|PICKED_UP|IN_TRANSIT|OUT_FOR_DELIVERY|DELIVERED|EXCEPTION|RETURNED
    
    # Tracking
    shipped_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    delivered_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    signature_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Documents
    packing_list_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    shipping_label_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    commercial_invoice_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    order: Mapped[SalesOrder] = relationship()
    customer: Mapped[Customer] = relationship()


class ShipmentLine(Base, HasId, HasCreatedAt):
    """Items in shipment"""
    __tablename__ = "sales_shipment_line"
    
    shipment_id: Mapped[str] = mapped_column(ForeignKey("sales_shipment.id"), nullable=False, index=True)
    order_line_id: Mapped[str] = mapped_column(ForeignKey("sales_order_line.id"), nullable=False, index=True)
    
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quantity_shipped: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Serial/Lot tracking
    lot_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    serial_numbers: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # List of serial #s
    
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    shipment: Mapped[Shipment] = relationship()
    order_line: Mapped[SalesOrderLine] = relationship()


# ============= PRICE LISTS =============

class PriceList(Base, HasId, HasCreatedAt):
    """Price list master"""
    __tablename__ = "sales_price_list"
    
    price_list_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    price_list_name: Mapped[str] = mapped_column(String(256), nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Effectivity
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    
    # Priority
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class PriceListLine(Base, HasId, HasCreatedAt):
    """Price list items"""
    __tablename__ = "sales_price_list_line"
    
    price_list_id: Mapped[str] = mapped_column(ForeignKey("sales_price_list.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Price
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Breaks
    min_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=1, nullable=False)
    max_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    price_list: Mapped[PriceList] = relationship()


# Add indexes
__table_args__ = (
    Index("ix_sales_order_customer_date", "customer_id", "order_date"),
    Index("ix_sales_order_status_priority", "status", "priority"),
    Index("ix_shipment_tracking", "carrier", "tracking_number"),
)
