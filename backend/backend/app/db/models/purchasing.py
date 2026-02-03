"""
MODULE: PURCHASING & PROCUREMENT
Complete purchase order management, vendor management, and receiving
"""

from __future__ import annotations

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Integer, Numeric, ForeignKey, JSON, Boolean, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ============= VENDOR MANAGEMENT =============

class Vendor(Base, HasId, HasCreatedAt):
    """Vendor/Supplier master"""
    __tablename__ = "purchase_vendor"
    
    # Basic Info
    vendor_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    vendor_type: Mapped[str] = mapped_column(String(32), default="SUPPLIER", nullable=False)
    # SUPPLIER|MANUFACTURER|DISTRIBUTOR|SERVICE_PROVIDER|CONTRACTOR
    
    # Classification
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tier: Mapped[str] = mapped_column(String(16), default="STANDARD", nullable=False)
    # STRATEGIC|PREFERRED|STANDARD|BACKUP
    
    # Contact
    primary_contact: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fax: Mapped[str | None] = mapped_column(String(32), nullable=True)
    website: Mapped[str | None] = mapped_column(String(256), nullable=True)
    
    # Address
    address_line1: Mapped[str | None] = mapped_column(String(256), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(256), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str] = mapped_column(String(3), default="USA", nullable=False)
    
    # Commercial Terms
    payment_terms: Mapped[str] = mapped_column(String(64), default="NET30", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    minimum_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Shipping
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    shipping_terms: Mapped[str | None] = mapped_column(String(32), nullable=True)  # FOB|CIF|DDP
    preferred_carrier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Tax
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    w9_on_file: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Performance Metrics
    on_time_delivery_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)  # %
    quality_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)  # 1-5
    last_audit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Approval
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Integration
    ap_vendor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    qms_supplier_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    # ACTIVE|INACTIVE|BLOCKED|PROBATION
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


# ============= PURCHASE REQUISITIONS =============

class PurchaseRequisition(Base, HasId, HasCreatedAt):
    """Internal purchase request"""
    __tablename__ = "purchase_requisition"
    
    requisition_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    requisition_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    required_by_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    
    # Requester
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cost_center_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Purpose
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Amounts
    estimated_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Status & Approval
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)
    # DRAFT|SUBMITTED|APPROVED|REJECTED|CONVERTED|CANCELLED
    
    approval_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Conversion
    converted_to_po_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    conversion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class PurchaseRequisitionLine(Base, HasId, HasCreatedAt):
    """Requisition line items"""
    __tablename__ = "purchase_requisition_line"
    
    requisition_id: Mapped[str] = mapped_column(ForeignKey("purchase_requisition.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Item
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Quantity
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Pricing
    estimated_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    estimated_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Suggested Vendor
    suggested_vendor_id: Mapped[str | None] = mapped_column(ForeignKey("purchase_vendor.id"), nullable=True)
    
    # GL Coding
    expense_account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cost_center_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    requisition: Mapped[PurchaseRequisition] = relationship()
    suggested_vendor: Mapped[Vendor | None] = relationship()


# ============= PURCHASE ORDERS =============

class PurchaseOrder(Base, HasId, HasCreatedAt):
    """Purchase order master"""
    __tablename__ = "purchase_order"
    
    po_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    po_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Vendor
    vendor_id: Mapped[str] = mapped_column(ForeignKey("purchase_vendor.id"), nullable=False, index=True)
    vendor_contact: Mapped[str | None] = mapped_column(String(256), nullable=True)
    vendor_quote_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Ship To
    ship_to_site_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ship_to_location_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ship_to_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    other_charges: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=1.0, nullable=False)
    
    # Terms
    payment_terms: Mapped[str] = mapped_column(String(64), nullable=False)
    shipping_terms: Mapped[str | None] = mapped_column(String(32), nullable=True)
    shipping_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Dates
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    promised_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)
    # DRAFT|SUBMITTED|ACKNOWLEDGED|IN_PRODUCTION|SHIPPED|PARTIALLY_RECEIVED|RECEIVED|CLOSED|CANCELLED
    
    approval_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    # PENDING|APPROVED|REJECTED
    
    # Approval Chain
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Buyer
    buyer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Source
    requisition_id: Mapped[str | None] = mapped_column(ForeignKey("purchase_requisition.id"), nullable=True)
    
    # Receiving Status
    received_quantity_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    invoiced_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Confirmations
    vendor_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledgment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Documents
    terms_and_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    vendor: Mapped[Vendor] = relationship()
    requisition: Mapped[PurchaseRequisition | None] = relationship()


class PurchaseOrderLine(Base, HasId, HasCreatedAt):
    """Purchase order line items"""
    __tablename__ = "purchase_order_line"
    
    po_id: Mapped[str] = mapped_column(ForeignKey("purchase_order.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Item
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    vendor_part_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Quantity
    quantity_ordered: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    quantity_rejected: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    quantity_cancelled: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Tax
    taxable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tax_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
    # Dates
    need_by_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    promised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # GL Coding
    expense_account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cost_center_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Quality
    inspection_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    inspection_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Status
    line_status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)
    # OPEN|PARTIALLY_RECEIVED|RECEIVED|CLOSED|CANCELLED
    
    # Source
    requisition_line_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    po: Mapped[PurchaseOrder] = relationship()


# ============= RECEIVING =============

class PurchaseReceipt(Base, HasId, HasCreatedAt):
    """Goods receipt / receiving document"""
    __tablename__ = "purchase_receipt"
    
    receipt_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    receipt_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # PO Reference
    po_id: Mapped[str] = mapped_column(ForeignKey("purchase_order.id"), nullable=False, index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("purchase_vendor.id"), nullable=False, index=True)
    
    # Shipment Info
    packing_slip_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    carrier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    # Location
    receiving_site_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    receiving_dock: Mapped[str | None] = mapped_column(String(64), nullable=True)
    staging_location_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Receiver
    received_by: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Inspection
    inspection_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    inspection_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # PENDING|IN_PROGRESS|PASSED|FAILED|CONDITIONAL
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="RECEIVED", nullable=False)
    # RECEIVED|INSPECTING|ACCEPTED|REJECTED|PUTAWAY|CLOSED
    
    # WMS Integration
    wms_receipt_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    putaway_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    po: Mapped[PurchaseOrder] = relationship()
    vendor: Mapped[Vendor] = relationship()


class PurchaseReceiptLine(Base, HasId, HasCreatedAt):
    """Receipt line items"""
    __tablename__ = "purchase_receipt_line"
    
    receipt_id: Mapped[str] = mapped_column(ForeignKey("purchase_receipt.id"), nullable=False, index=True)
    po_line_id: Mapped[str] = mapped_column(ForeignKey("purchase_order_line.id"), nullable=False, index=True)
    
    # Item
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Quantity
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_accepted: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    quantity_rejected: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Lot/Serial
    lot_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    serial_numbers: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    
    # Inspection
    inspection_result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # PASS|FAIL|CONDITIONAL
    
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Location
    putaway_location_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    handling_unit_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    receipt: Mapped[PurchaseReceipt] = relationship()
    po_line: Mapped[PurchaseOrderLine] = relationship()


# ============= VENDOR CATALOG =============

class VendorCatalog(Base, HasId, HasCreatedAt):
    """Vendor's catalog of items they can supply"""
    __tablename__ = "purchase_vendor_catalog"
    
    vendor_id: Mapped[str] = mapped_column(ForeignKey("purchase_vendor.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Vendor Details
    vendor_part_number: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Minimum Order
    minimum_order_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    order_multiple: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    # Lead Time
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Preferred
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Effectivity
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    vendor: Mapped[Vendor] = relationship()


# Add indexes
__table_args__ = (
    Index("ix_po_vendor_date", "vendor_id", "po_date"),
    Index("ix_po_status_date", "status", "expected_delivery_date"),
    Index("ix_receipt_po_date", "po_id", "receipt_date"),
)
