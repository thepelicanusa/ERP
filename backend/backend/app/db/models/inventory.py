"""
MODULE: INVENTORY MANAGEMENT
Advanced inventory planning, control, and optimization
Extends basic WMS inventory with planning and analytics features
"""

from __future__ import annotations

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Integer, Numeric, ForeignKey, JSON, Boolean, Index, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ============= ITEM MASTER (Extended) =============

class InventoryItem(Base, HasId, HasCreatedAt):
    """
    Extended item master with inventory planning attributes
    Extends wms_item with planning, costing, and control features
    """
    __tablename__ = "inv_item_master"
    
    # Link to WMS Item
    wms_item_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    item_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    
    # Classification
    item_type: Mapped[str] = mapped_column(String(32), default="FINISHED_GOOD", nullable=False)
    # FINISHED_GOOD|RAW_MATERIAL|WIP|COMPONENT|CONSUMABLE|TOOL|SERVICE
    
    item_category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    product_line: Mapped[str | None] = mapped_column(String(64), nullable=True)
    abc_class: Mapped[str] = mapped_column(String(1), default="C", nullable=False, index=True)  # A|B|C
    
    # Unit of Measure
    base_uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    weight_uom: Mapped[str] = mapped_column(String(8), default="LBS", nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    volume_uom: Mapped[str] = mapped_column(String(8), default="CUFT", nullable=False)
    
    # Costing
    cost_method: Mapped[str] = mapped_column(String(16), default="AVERAGE", nullable=False)
    # STANDARD|AVERAGE|FIFO|LIFO
    
    standard_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    average_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    last_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    # Planning Parameters
    replenishment_method: Mapped[str] = mapped_column(String(32), default="REORDER_POINT", nullable=False)
    # REORDER_POINT|MIN_MAX|MRP|MANUAL
    
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    safety_lead_time_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Safety Stock
    safety_stock_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    safety_stock_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # FIXED|DAYS_OF_SUPPLY|STATISTICAL
    safety_stock_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Reorder Point & Min/Max
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    reorder_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    minimum_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    maximum_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    
    # Order Multiples
    order_multiple: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    minimum_order_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    maximum_order_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    # Make vs Buy
    make_or_buy: Mapped[str] = mapped_column(String(16), default="BUY", nullable=False)
    # MAKE|BUY|BOTH
    
    # Tracking
    lot_control: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    serial_control: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revision_control: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Shelf Life
    perishable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Status Control
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_purchasable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_saleable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_manufacturable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Lifecycle
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    # DEVELOPMENT|ACTIVE|PHASE_OUT|OBSOLETE|DISCONTINUED
    
    phase_out_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    obsolete_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    replacement_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Demand History (for forecasting)
    last_demand_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    average_monthly_demand: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    # Last Activity
    last_receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_count_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


# ============= INVENTORY PLANNING =============

class InventoryPlanningProfile(Base, HasId, HasCreatedAt):
    """
    Planning profiles for different item/location combinations
    Allows different planning parameters per site or customer
    """
    __tablename__ = "inv_planning_profile"
    
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    
    # Scope
    site_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    location_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Planning Override
    override_reorder_point: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    override_min_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    override_max_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    override_safety_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    override_lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Demand Pattern
    demand_pattern: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # STEADY|SEASONAL|INTERMITTENT|LUMPY|DECLINING
    
    seasonal_factor: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    item: Mapped[InventoryItem] = relationship()


# ============= INVENTORY VALUATION =============

class InventoryValuation(Base, HasId, HasCreatedAt):
    """
    Snapshot of inventory value at a point in time
    Used for financial reporting and variance analysis
    """
    __tablename__ = "inv_valuation_snapshot"
    
    valuation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # MONTH_END|QUARTER_END|YEAR_END|PHYSICAL_COUNT|AD_HOC
    
    # Scope
    site_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    item_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Totals
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Method
    valuation_method: Mapped[str] = mapped_column(String(16), nullable=False)
    # STANDARD|AVERAGE|FIFO|LIFO
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)
    # DRAFT|POSTED|CLOSED
    
    posted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # GL Integration
    gl_journal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class InventoryValuationLine(Base, HasId, HasCreatedAt):
    """
    Detail lines for inventory valuation
    """
    __tablename__ = "inv_valuation_line"
    
    valuation_id: Mapped[str] = mapped_column(ForeignKey("inv_valuation_snapshot.id"), nullable=False, index=True)
    
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    location_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Quantities
    on_hand_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reserved_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    available_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    
    # Costing
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    extended_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Variance (if physical count)
    counted_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    variance_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    variance_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    valuation: Mapped[InventoryValuation] = relationship()
    item: Mapped[InventoryItem] = relationship()


# ============= ABC ANALYSIS =============

class ABCAnalysis(Base, HasId, HasCreatedAt):
    """
    ABC classification analysis results
    Run periodically to classify items by value/usage
    """
    __tablename__ = "inv_abc_analysis"
    
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    analysis_period_months: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    
    # Criteria
    criteria: Mapped[str] = mapped_column(String(32), nullable=False)
    # VALUE|USAGE|REVENUE|MARGIN
    
    # Thresholds
    a_threshold_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=80, nullable=False)
    b_threshold_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=95, nullable=False)
    # C is the remainder
    
    # Results
    total_items_analyzed: Mapped[int] = mapped_column(Integer, nullable=False)
    a_items_count: Mapped[int] = mapped_column(Integer, nullable=False)
    b_items_count: Mapped[int] = mapped_column(Integer, nullable=False)
    c_items_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="COMPLETED", nullable=False)
    applied_to_items: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    performed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ABCAnalysisLine(Base, HasId, HasCreatedAt):
    """
    Item-level ABC classification results
    """
    __tablename__ = "inv_abc_analysis_line"
    
    analysis_id: Mapped[str] = mapped_column(ForeignKey("inv_abc_analysis.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    
    # Metrics
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    
    # Ranking
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    cumulative_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    
    # Classification
    abc_class: Mapped[str] = mapped_column(String(1), nullable=False)  # A|B|C
    previous_abc_class: Mapped[str | None] = mapped_column(String(1), nullable=True)
    
    analysis: Mapped[ABCAnalysis] = relationship()
    item: Mapped[InventoryItem] = relationship()


# ============= SLOW MOVING & OBSOLESCENCE =============

class SlowMovingAnalysis(Base, HasId, HasCreatedAt):
    """
    Identify slow-moving and obsolete inventory
    """
    __tablename__ = "inv_slow_moving_analysis"
    
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    lookback_months: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    
    # Thresholds
    no_movement_months: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    slow_moving_threshold: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    # Units per month
    
    # Results
    total_items_analyzed: Mapped[int] = mapped_column(Integer, nullable=False)
    no_movement_items: Mapped[int] = mapped_column(Integer, nullable=False)
    slow_moving_items: Mapped[int] = mapped_column(Integer, nullable=False)
    
    total_value_at_risk: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    performed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class SlowMovingItem(Base, HasId, HasCreatedAt):
    """
    Items flagged as slow-moving or obsolete
    """
    __tablename__ = "inv_slow_moving_item"
    
    analysis_id: Mapped[str] = mapped_column(ForeignKey("inv_slow_moving_analysis.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    
    # Current State
    on_hand_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    on_hand_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Activity
    last_receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    days_since_last_movement: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Usage
    usage_last_12_months: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    months_of_supply: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Classification
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    # NO_MOVEMENT|SLOW_MOVING|EXCESS|OBSOLETE
    
    # Recommendation
    recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # DISPOSE|RETURN_TO_VENDOR|DISCOUNT_SALE|REWORK|SCRAP
    
    # Disposition
    disposition_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    # PENDING|APPROVED|IN_PROGRESS|COMPLETED
    
    disposition_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    write_off_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    analysis: Mapped[SlowMovingAnalysis] = relationship()
    item: Mapped[InventoryItem] = relationship()


# ============= INVENTORY ADJUSTMENT =============

class InventoryAdjustment(Base, HasId, HasCreatedAt):
    """
    Physical inventory adjustments (non-transactional)
    For corrections, write-offs, etc.
    """
    __tablename__ = "inv_adjustment"
    
    adjustment_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    adjustment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Reason
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    # CYCLE_COUNT_VARIANCE|DAMAGE|SHRINKAGE|OBSOLESCENCE|ERROR_CORRECTION|WRITE_OFF
    
    reason_description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Approval
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    # PENDING|APPROVED|REJECTED
    
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Totals
    total_quantity_adjusted: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    total_value_impact: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False)
    # DRAFT|POSTED|REVERSED
    
    posted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Integration
    wms_txn_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gl_journal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class InventoryAdjustmentLine(Base, HasId, HasCreatedAt):
    """
    Line items for inventory adjustments
    """
    __tablename__ = "inv_adjustment_line"
    
    adjustment_id: Mapped[str] = mapped_column(ForeignKey("inv_adjustment.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    location_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    # Adjustment
    quantity_before: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_after: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_adjustment: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    
    # Costing
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    value_adjustment: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # GL Coding
    adjustment_account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cost_center_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    adjustment: Mapped[InventoryAdjustment] = relationship()
    item: Mapped[InventoryItem] = relationship()


# ============= STOCK STATUS & AVAILABILITY =============

class StockStatusSummary(Base, HasId, HasCreatedAt):
    """
    Real-time summary of stock status by item/location
    Materialized view for quick lookups
    """
    __tablename__ = "inv_stock_status"
    
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    site_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    location_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Quantities
    on_hand_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    reserved_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    available_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    
    on_order_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    in_transit_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    
    # Quality Hold
    quarantine_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    hold_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    
    # Planning
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    
    # Status Flags
    is_below_safety_stock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_below_reorder_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_overstock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Last Updated
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    item: Mapped[InventoryItem] = relationship()


# Add indexes and constraints
__table_args__ = (
    Index("ix_inv_item_abc_status", "abc_class", "lifecycle_status"),
    Index("ix_inv_item_category_active", "item_category", "is_active"),
    Index("ix_stock_status_item_site", "item_id", "site_id"),
    CheckConstraint("available_qty >= 0", name="ck_available_non_negative"),
)
