from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import String, DateTime, JSON, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt

class Forecast(Base, HasId, HasCreatedAt):
    __tablename__ = "plan_forecast"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # inv_item_master.id
    period_start: Mapped[date] = mapped_column(nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(String(16), default="WEEK", nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_forecast_item_period", Forecast.item_id, Forecast.period_start)

class MRPNettingRun(Base, HasId, HasCreatedAt):
    __tablename__ = "plan_mrp_run"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="DONE", nullable=False, index=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    results: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class PlannedOrder(Base, HasId, HasCreatedAt):
    __tablename__ = "plan_planned_order"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # MAKE/BUY
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PLANNED", nullable=False, index=True)  # PLANNED/FIRM
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_planned_item_due", PlannedOrder.item_id, PlannedOrder.due_date)

class CapacityBucket(Base, HasId, HasCreatedAt):
    __tablename__ = "plan_capacity_bucket"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    work_center_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # mes_work_center.id
    bucket_start: Mapped[date] = mapped_column(nullable=False, index=True)
    minutes_available: Mapped[int] = mapped_column(nullable=False, default=0)
    minutes_required: Mapped[int] = mapped_column(nullable=False, default=0)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_capacity_wc_bucket", CapacityBucket.work_center_id, CapacityBucket.bucket_start)

class ExceptionMessage(Base, HasId, HasCreatedAt):
    __tablename__ = "plan_exception"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(8), default="WARN", nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

# ============================================================================
# WMS Wave Planning (minimal models for import/boot stability)
# ============================================================================
# services.wms.inventory_ops.wave_api expects:
#   from app.db.models.planning import Wave, WaveOrder
#
# These are minimal entities; we can expand schema later (allocations, batching rules, etc.).

class Wave(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_wave"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False, index=True)  # OPEN|RELEASED|DONE|CANCELLED
    wave_type: Mapped[str] = mapped_column(String(24), default="PICK", nullable=False, index=True)  # PICK|PUTAWAY|RECEIVE|COUNT
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class WaveOrder(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_wave_order"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    wave_id: Mapped[str] = mapped_column(ForeignKey("wms_wave.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # docs.Order.id (or OutboundOrder)
    status: Mapped[str] = mapped_column(String(24), default="ALLOCATED", nullable=False, index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_wms_wave_order_wave_created", WaveOrder.wave_id, WaveOrder.created_at)


# ============================================================================
# Backorder (minimal model for allocation / boot stability)
# ============================================================================
# services.wms.inventory_ops.allocation_service expects:
#   from app.db.models.planning import Backorder
#
# Minimal representation; can be expanded later (links to waves, pick tasks, etc.).

class Backorder(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_backorder"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)   # docs.Order.id / OutboundOrder
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)    # inv_item_master.id
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # SHORT_PICK|NO_STOCK|HOLD|OTHER
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False, index=True)  # OPEN|RESOLVED|CANCELLED
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_wms_backorder_order_item", Backorder.order_id, Backorder.item_id)

