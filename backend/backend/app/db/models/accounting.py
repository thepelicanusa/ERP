# Complete Enterprise Backend Architecture
# Extends existing WMS/MES with Accounting, QMS, MRP, eCommerce, HRMS

"""
File: apps/api/app/db/models/accounting.py
Complete Accounting Module - GL, AP, AR, Cost Accounting
"""

from __future__ import annotations

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Integer, Numeric, ForeignKey, Enum, JSON, Boolean, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt
from typing import Optional

# ============= CHART OF ACCOUNTS =============
class GLAccount(Base, HasId, HasCreatedAt):
    __tablename__ = "gl_account"
    
    account_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    account_name: Mapped[str] = mapped_column(String(256), nullable=False)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)  # ASSET|LIABILITY|EQUITY|REVENUE|EXPENSE|COGS
    account_subtype: Mapped[str | None] = mapped_column(String(64), nullable=True)  # CURRENT_ASSET|FIXED_ASSET|etc
    parent_account_id: Mapped[str | None] = mapped_column(ForeignKey("gl_account.id"), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_control_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tax_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    parent_account: Mapped[Optional["GLAccount"]] = relationship(remote_side="GLAccount.id")

# ============= GENERAL LEDGER =============
class GLJournal(Base, HasId, HasCreatedAt):
    __tablename__ = "gl_journal"
    
    journal_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    journal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    posting_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # 2024-01
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    journal_type: Mapped[str] = mapped_column(String(32), nullable=False)  # MANUAL|AUTO|RECURRING|ADJUSTMENT|CLOSING
    source_module: Mapped[str | None] = mapped_column(String(32), nullable=True)  # AP|AR|INVENTORY|PAYROLL|etc
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)  # DRAFT|POSTED|REVERSED|VOID
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    posted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_journal_id: Mapped[str | None] = mapped_column(ForeignKey("gl_journal.id"), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class GLJournalLine(Base, HasId, HasCreatedAt):
    __tablename__ = "gl_journal_line"
    
    journal_id: Mapped[str] = mapped_column(ForeignKey("gl_journal.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("gl_account.id"), nullable=False, index=True)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=1.0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_center_id: Mapped[str | None] = mapped_column(ForeignKey("gl_cost_center.id"), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    department_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    dimension1: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Custom dimensions
    dimension2: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    journal: Mapped[GLJournal] = relationship()
    account: Mapped[GLAccount] = relationship()
    cost_center: Mapped[Optional["GLCostCenter"]] = relationship()

Index("ix_gl_journal_line_journal_line", GLJournalLine.journal_id, GLJournalLine.line_number)

# ============= COST CENTERS & BUDGETS =============
class GLCostCenter(Base, HasId, HasCreatedAt):
    __tablename__ = "gl_cost_center"
    
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("gl_cost_center.id"), nullable=True)
    manager_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # FK to employee
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    parent: Mapped[Optional["GLCostCenter"]] = relationship(remote_side="GLCostCenter.id")

class GLBudget(Base, HasId, HasCreatedAt):
    __tablename__ = "gl_budget"
    
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # 2024-01 or ANNUAL
    account_id: Mapped[str] = mapped_column(ForeignKey("gl_account.id"), nullable=False, index=True)
    cost_center_id: Mapped[str | None] = mapped_column(ForeignKey("gl_cost_center.id"), nullable=True, index=True)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    variance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)  # DRAFT|APPROVED|LOCKED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    account: Mapped[GLAccount] = relationship()
    cost_center: Mapped[GLCostCenter | None] = relationship()

Index("ix_gl_budget_year_period_account", GLBudget.fiscal_year, GLBudget.period, GLBudget.account_id)

# ============= ACCOUNTS PAYABLE =============
class APVendor(Base, HasId, HasCreatedAt):
    __tablename__ = "ap_vendor"
    
    vendor_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    vendor_type: Mapped[str] = mapped_column(String(32), default="SUPPLIER", nullable=False)  # SUPPLIER|SERVICE|CONTRACTOR
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(64), default="NET30", nullable=False)  # NET15|NET30|NET60|COD
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Contact Info
    contact_person: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
    # Address
    address_line1: Mapped[str | None] = mapped_column(String(256), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(256), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str] = mapped_column(String(3), default="USA", nullable=False)
    
    # GL Integration
    ap_account_id: Mapped[str | None] = mapped_column(ForeignKey("gl_account.id"), nullable=True)
    
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)  # ACTIVE|INACTIVE|BLOCKED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    ap_account: Mapped[GLAccount | None] = relationship()

class APInvoice(Base, HasId, HasCreatedAt):
    __tablename__ = "ap_invoice"
    
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    vendor_invoice_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("ap_vendor.id"), nullable=False, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_terms: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)  # PENDING|APPROVED|PAID|VOID|DISPUTED
    
    # Approval workflow
    approval_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Source document (e.g., Purchase Order)
    source_document_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # GL Integration
    gl_journal_id: Mapped[str | None] = mapped_column(ForeignKey("gl_journal.id"), nullable=True)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    vendor: Mapped[APVendor] = relationship()
    gl_journal: Mapped[GLJournal | None] = relationship()

class APInvoiceLine(Base, HasId, HasCreatedAt):
    __tablename__ = "ap_invoice_line"
    
    invoice_id: Mapped[str] = mapped_column(ForeignKey("ap_invoice.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    
    # Quantity & Price
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Item reference (optional - for inventory items)
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # GL Coding
    expense_account_id: Mapped[str | None] = mapped_column(ForeignKey("gl_account.id"), nullable=True)
    cost_center_id: Mapped[str | None] = mapped_column(ForeignKey("gl_cost_center.id"), nullable=True)
    
    tax_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    invoice: Mapped[APInvoice] = relationship()
    expense_account: Mapped[GLAccount | None] = relationship()
    cost_center: Mapped[GLCostCenter | None] = relationship()

class APPayment(Base, HasId, HasCreatedAt):
    __tablename__ = "ap_payment"
    
    payment_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("ap_vendor.id"), nullable=False, index=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)  # CHECK|ACH|WIRE|CREDIT_CARD|CASH
    payment_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Payment details
    check_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bank_account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)  # PENDING|CLEARED|VOID
    cleared_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # GL Integration
    gl_journal_id: Mapped[str | None] = mapped_column(ForeignKey("gl_journal.id"), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    vendor: Mapped[APVendor] = relationship()
    gl_journal: Mapped[GLJournal | None] = relationship()

class APPaymentAllocation(Base, HasId, HasCreatedAt):
    __tablename__ = "ap_payment_allocation"
    
    payment_id: Mapped[str] = mapped_column(ForeignKey("ap_payment.id"), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("ap_invoice.id"), nullable=False, index=True)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_taken: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    payment: Mapped[APPayment] = relationship()
    invoice: Mapped[APInvoice] = relationship()

# ============= ACCOUNTS RECEIVABLE =============
class ARCustomer(Base, HasId, HasCreatedAt):
    __tablename__ = "ar_customer"
    
    customer_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    customer_type: Mapped[str] = mapped_column(String(32), default="RETAIL", nullable=False)  # RETAIL|WHOLESALE|DISTRIBUTOR
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(64), default="NET30", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Contact
    contact_person: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
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
    
    # GL Integration
    ar_account_id: Mapped[str | None] = mapped_column(ForeignKey("gl_account.id"), nullable=True)
    
    # eCommerce integration
    ecommerce_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    ar_account: Mapped[GLAccount | None] = relationship()

class ARInvoice(Base, HasId, HasCreatedAt):
    __tablename__ = "ar_invoice"
    
    invoice_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("ar_customer.id"), nullable=False, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_terms: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)  # PENDING|SENT|PAID|OVERDUE|VOID|WRITTEN_OFF
    
    # Source (Sales Order, eCommerce Order)
    source_document_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # GL Integration
    gl_journal_id: Mapped[str | None] = mapped_column(ForeignKey("gl_journal.id"), nullable=True)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    customer: Mapped[ARCustomer] = relationship()
    gl_journal: Mapped[GLJournal | None] = relationship()

class ARInvoiceLine(Base, HasId, HasCreatedAt):
    __tablename__ = "ar_invoice_line"
    
    invoice_id: Mapped[str] = mapped_column(ForeignKey("ar_invoice.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Item reference
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # GL Coding
    revenue_account_id: Mapped[str | None] = mapped_column(ForeignKey("gl_account.id"), nullable=True)
    
    tax_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    invoice: Mapped[ARInvoice] = relationship()
    revenue_account: Mapped[GLAccount | None] = relationship()

class ARPayment(Base, HasId, HasCreatedAt):
    __tablename__ = "ar_payment"
    
    payment_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("ar_customer.id"), nullable=False, index=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)  # CHECK|ACH|WIRE|CREDIT_CARD|CASH|PAYPAL
    payment_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Payment details
    check_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)  # For online payments
    
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)  # PENDING|CLEARED|NSF|VOID
    cleared_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # GL Integration
    gl_journal_id: Mapped[str | None] = mapped_column(ForeignKey("gl_journal.id"), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    customer: Mapped[ARCustomer] = relationship()
    gl_journal: Mapped[GLJournal | None] = relationship()

class ARPaymentAllocation(Base, HasId, HasCreatedAt):
    __tablename__ = "ar_payment_allocation"
    
    payment_id: Mapped[str] = mapped_column(ForeignKey("ar_payment.id"), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("ar_invoice.id"), nullable=False, index=True)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_taken: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    payment: Mapped[ARPayment] = relationship()
    invoice: Mapped[ARInvoice] = relationship()

# ============= COST ACCOUNTING =============
class CostPool(Base, HasId, HasCreatedAt):
    __tablename__ = "cost_pool"
    
    pool_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    pool_name: Mapped[str] = mapped_column(String(256), nullable=False)
    pool_type: Mapped[str] = mapped_column(String(32), nullable=False)  # OVERHEAD|LABOR|MATERIAL|MACHINE
    allocation_method: Mapped[str] = mapped_column(String(32), nullable=False)  # DIRECT_LABOR_HOURS|MACHINE_HOURS|UNITS|CUSTOM
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class ProductCost(Base, HasId, HasCreatedAt):
    __tablename__ = "product_cost"
    
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # FK to wms_item
    cost_type: Mapped[str] = mapped_column(String(32), nullable=False)  # STANDARD|ACTUAL|AVERAGE
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Cost components
    material_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    overhead_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_product_cost_item_date", ProductCost.item_id, ProductCost.effective_date)

class CostVariance(Base, HasId, HasCreatedAt):
    __tablename__ = "cost_variance"
    
    variance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cost_pool_id: Mapped[str | None] = mapped_column(ForeignKey("cost_pool.id"), nullable=True)
    variance_type: Mapped[str] = mapped_column(String(32), nullable=False)  # PRICE|EFFICIENCY|VOLUME|MIX
    
    standard_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    variance_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    variance_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    cost_pool: Mapped[CostPool | None] = relationship()
