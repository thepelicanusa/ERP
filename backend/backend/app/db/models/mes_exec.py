from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, JSON, ForeignKey, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt

class WorkCenter(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_work_center"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_mes_wc_tenant_code", WorkCenter.tenant_id, WorkCenter.code)

class Routing(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_routing"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class RoutingOperation(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_routing_operation"
    routing_id: Mapped[str] = mapped_column(ForeignKey("mes_routing.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(nullable=False)
    op_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    work_center_id: Mapped[str] = mapped_column(ForeignKey("mes_work_center.id"), nullable=False, index=True)
    std_time_min: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    routing: Mapped[Routing] = relationship()
    work_center: Mapped[WorkCenter] = relationship()

Index("ix_mes_routeop_routing_seq", RoutingOperation.routing_id, RoutingOperation.sequence)

class ProductionOrder(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_production_order"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # inv_item_master.id
    routing_id: Mapped[str | None] = mapped_column(ForeignKey("mes_routing.id"), nullable=True, index=True)
    qty_planned: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    qty_completed: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PLANNED", nullable=False, index=True)  # RELEASED/IN_PROGRESS/DONE
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class ProductionOperation(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_production_operation"
    prod_order_id: Mapped[str] = mapped_column(ForeignKey("mes_production_order.id"), nullable=False, index=True)
    routing_op_id: Mapped[str] = mapped_column(ForeignKey("mes_routing_operation.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="READY", nullable=False, index=True)  # READY/RUNNING/DONE
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_mes_prodop_order_seq", ProductionOperation.prod_order_id, ProductionOperation.sequence)

class ProductionMaterial(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_production_material"
    prod_order_id: Mapped[str] = mapped_column(ForeignKey("mes_production_order.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # inv_item_master.id
    qty_required: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    qty_issued: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class ProductionLabor(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_production_labor"
    prod_op_id: Mapped[str] = mapped_column(ForeignKey("mes_production_operation.id"), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    minutes: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class ProductionScrap(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_production_scrap"
    prod_op_id: Mapped[str] = mapped_column(ForeignKey("mes_production_operation.id"), nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class ProductionQualityCheck(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_production_qc"
    prod_op_id: Mapped[str] = mapped_column(ForeignKey("mes_production_operation.id"), nullable=False, index=True)
    check_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # PASS/FAIL/HOLD
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_mes_qc_op_code", ProductionQualityCheck.prod_op_id, ProductionQualityCheck.check_code)
