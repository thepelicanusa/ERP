"""
File: apps/api/app/db/models/mrp.py
Material Requirements Planning + Production Management
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

# ============= BILL OF MATERIALS (BOM) =============
class MRPBOM(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_bom"
    
    bom_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    parent_item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # FK to wms_item
    bom_type: Mapped[str] = mapped_column(String(32), default="PRODUCTION", nullable=False)  # PRODUCTION|ENGINEERING|PLANNING
    
    # Version Control
    revision: Mapped[str] = mapped_column(String(16), default="A", nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    obsolete_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    
    # Production Details
    base_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=1, nullable=False)
    base_uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Yield & Scrap
    standard_yield_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=100, nullable=False)
    scrap_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0, nullable=False)
    
    # Routing
    routing_id: Mapped[str | None] = mapped_column(ForeignKey("mrp_routing.id"), nullable=True)
    
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)  # ACTIVE|DRAFT|OBSOLETE
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    routing: Mapped[Optional["MRPRouting"]] = relationship()

class MRPBOMLine(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_bom_line"
    
    bom_id: Mapped[str] = mapped_column(ForeignKey("mrp_bom.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Component
    component_item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # FK to wms_item
    component_type: Mapped[str] = mapped_column(String(32), default="MATERIAL", nullable=False)  # MATERIAL|SUB_ASSEMBLY|PHANTOM|REFERENCE
    
    # Quantity
    quantity_per: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    scrap_factor: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0, nullable=False)
    
    # Planning
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lead_time_offset_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Substitutes
    substitute_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    substitute_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    
    # Operation tie-in
    operation_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Which routing operation consumes this
    
    # Effectivity
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    obsolete_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    bom: Mapped[MRPBOM] = relationship()

Index("ix_mrp_bom_line_bom_line", MRPBOMLine.bom_id, MRPBOMLine.line_number)

# ============= ROUTING (Process Steps) =============
class MRPRouting(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_routing"
    
    routing_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # FK to wms_item
    routing_type: Mapped[str] = mapped_column(String(32), default="STANDARD", nullable=False)  # STANDARD|ALTERNATE|REWORK
    
    revision: Mapped[str] = mapped_column(String(16), default="A", nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    obsolete_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Lead Times
    fixed_lead_time_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    variable_lead_time_hours: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0, nullable=False)
    queue_time_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class MRPRoutingOperation(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_routing_operation"
    
    routing_id: Mapped[str] = mapped_column(ForeignKey("mrp_routing.id"), nullable=False, index=True)
    operation_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_code: Mapped[str] = mapped_column(String(32), nullable=False)
    operation_description: Mapped[str] = mapped_column(String(256), nullable=False)
    
    # Work Center
    work_center_id: Mapped[str] = mapped_column(ForeignKey("mrp_work_center.id"), nullable=False, index=True)
    
    # Times (per base quantity)
    setup_time_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    run_time_hours: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    teardown_time_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    queue_time_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    
    # Labor
    labor_hours_per_unit: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0, nullable=False)
    labor_rate_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    
    # Overhead
    overhead_rate_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    
    # Quality
    inspection_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    inspection_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Dependencies
    predecessor_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Previous operation that must complete
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    routing: Mapped[MRPRouting] = relationship()
    work_center: Mapped["MRPWorkCenter"] = relationship()

Index("ix_mrp_routing_op_routing_seq", MRPRoutingOperation.routing_id, MRPRoutingOperation.operation_sequence)

# ============= WORK CENTERS & RESOURCES =============
class MRPWorkCenter(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_work_center"
    
    work_center_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    work_center_name: Mapped[str] = mapped_column(String(256), nullable=False)
    work_center_type: Mapped[str] = mapped_column(String(32), nullable=False)  # MACHINE|ASSEMBLY|INSPECTION|PACKAGING
    
    # Capacity
    capacity_uom: Mapped[str] = mapped_column(String(16), default="HOURS", nullable=False)
    capacity_per_day: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    efficiency_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=100, nullable=False)
    utilization_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=80, nullable=False)
    
    # Costs
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    overhead_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    
    # Location
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    # Calendar
    calendar_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

# ============= MRP PLANNING =============
class MRPDemand(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_demand"
    
    demand_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    demand_type: Mapped[str] = mapped_column(String(32), nullable=False)  # SALES_ORDER|FORECAST|SAFETY_STOCK|PRODUCTION_ORDER
    demand_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Source
    source_document_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Priority
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_firm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Can't be rescheduled
    
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)  # OPEN|PLANNED|RELEASED|CLOSED
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_mrp_demand_item_date", MRPDemand.item_id, MRPDemand.demand_date)

class MRPSupply(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_supply"
    
    supply_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    supply_type: Mapped[str] = mapped_column(String(32), nullable=False)  # PURCHASE_ORDER|PRODUCTION_ORDER|TRANSFER_ORDER|ON_HAND
    supply_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Source
    source_document_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Allocation
    allocated_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    available_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    
    status: Mapped[str] = mapped_column(String(16), default="PLANNED", nullable=False)  # PLANNED|RELEASED|IN_PROGRESS|RECEIVED|CLOSED
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_mrp_supply_item_date", MRPSupply.item_id, MRPSupply.supply_date)

class MRPPlannedOrder(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_planned_order"
    
    planned_order_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    order_type: Mapped[str] = mapped_column(String(32), nullable=False)  # PURCHASE|PRODUCTION|TRANSFER
    
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Dates
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Source Demand
    demand_ids: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # List of demand IDs this fulfills
    
    # Pegging
    pegged_to_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Parent item in BOM explosion
    pegged_to_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Firming
    is_firm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    firmed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Conversion
    converted_to_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # PO|PRODUCTION_ORDER
    converted_to_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    converted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    status: Mapped[str] = mapped_column(String(16), default="SUGGESTED", nullable=False)  # SUGGESTED|FIRM|RELEASED|CONVERTED|CANCELLED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

# ============= PRODUCTION ORDERS =============
class MRPProductionOrder(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_production_order"
    
    production_order_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Product
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bom_id: Mapped[str] = mapped_column(ForeignKey("mrp_bom.id"), nullable=False)
    routing_id: Mapped[str | None] = mapped_column(ForeignKey("mrp_routing.id"), nullable=True)
    
    # Quantities
    ordered_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    produced_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    scrapped_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Schedule
    scheduled_start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scheduled_end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    actual_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Source
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # SALES_ORDER|MRP|MANUAL
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Priority
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    
    # Costs (Actuals)
    actual_material_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    actual_labor_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    actual_overhead_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    # WMS Integration
    output_location_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Where finished goods go
    
    status: Mapped[str] = mapped_column(String(16), default="PLANNED", nullable=False)  # PLANNED|RELEASED|IN_PROGRESS|COMPLETED|CLOSED|CANCELLED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    bom: Mapped[MRPBOM] = relationship()
    routing: Mapped[MRPRouting | None] = relationship()

class MRPProductionOrderLine(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_production_order_line"
    
    production_order_id: Mapped[str] = mapped_column(ForeignKey("mrp_production_order.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    line_type: Mapped[str] = mapped_column(String(16), nullable=False)  # MATERIAL|LABOR|OVERHEAD
    
    # Material Line
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    issued_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    consumed_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Location (for material issue)
    from_location_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Backflush
    is_backflushed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Cost
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)  # PENDING|ISSUED|CONSUMED|CANCELLED
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    production_order: Mapped[MRPProductionOrder] = relationship()

Index("ix_mrp_po_line_po_line", MRPProductionOrderLine.production_order_id, MRPProductionOrderLine.line_number)

class MRPProductionOrderOperation(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_production_order_operation"
    
    production_order_id: Mapped[str] = mapped_column(ForeignKey("mrp_production_order.id"), nullable=False, index=True)
    operation_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Operation Details
    routing_operation_id: Mapped[str | None] = mapped_column(ForeignKey("mrp_routing_operation.id"), nullable=True)
    work_center_id: Mapped[str] = mapped_column(ForeignKey("mrp_work_center.id"), nullable=False)
    operation_description: Mapped[str] = mapped_column(String(256), nullable=False)
    
    # Times (Planned)
    planned_setup_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    planned_run_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    planned_teardown_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    
    # Times (Actual)
    actual_setup_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    actual_run_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    actual_teardown_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    
    # Schedule
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Quantities
    quantity_completed: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    quantity_scrapped: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    
    # Assignment
    assigned_operator: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)  # PENDING|READY|IN_PROGRESS|COMPLETED|SKIPPED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    production_order: Mapped[MRPProductionOrder] = relationship()
    routing_operation: Mapped[MRPRoutingOperation | None] = relationship()
    work_center: Mapped[MRPWorkCenter] = relationship()

Index("ix_mrp_po_op_po_seq", MRPProductionOrderOperation.production_order_id, MRPProductionOrderOperation.operation_sequence)

# ============= CAPACITY PLANNING =============
class MRPCapacityRequirement(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_capacity_requirement"
    
    requirement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    work_center_id: Mapped[str] = mapped_column(ForeignKey("mrp_work_center.id"), nullable=False, index=True)
    
    # Source
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # PRODUCTION_ORDER|PLANNED_ORDER
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operation_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Capacity
    required_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    work_center: Mapped[MRPWorkCenter] = relationship()

Index("ix_mrp_capacity_date_wc", MRPCapacityRequirement.requirement_date, MRPCapacityRequirement.work_center_id)

# ============= FORECASTING =============
class MRPForecast(Base, HasId, HasCreatedAt):
    __tablename__ = "mrp_forecast"
    
    forecast_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    forecast_period: Mapped[str] = mapped_column(String(16), nullable=False)  # DAILY|WEEKLY|MONTHLY
    
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    forecasted_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    consumed_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    
    # Method
    forecast_method: Mapped[str] = mapped_column(String(32), nullable=False)  # MANUAL|MOVING_AVERAGE|LINEAR_REGRESSION|SEASONAL
    confidence_level: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)  # Percentage
    
    # Source
    customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sales_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_mrp_forecast_item_date", MRPForecast.item_id, MRPForecast.forecast_date)

# ============================================================================
# Backward compatibility exports (API import stability)
# ============================================================================
# API layer expects generic names:
#   BOM, BOMLine, Routing, RoutingOperation, WorkCenter
# Canonical models in this module are MRP-prefixed.
BOM = MRPBOM
BOMLine = MRPBOMLine
Routing = MRPRouting
RoutingOperation = MRPRoutingOperation
WorkCenter = MRPWorkCenter

