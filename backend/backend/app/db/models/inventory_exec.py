from __future__ import annotations
from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from sqlalchemy import String, DateTime, JSON, ForeignKey, Numeric, Index, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt
from app.db.models.inventory import InventoryItem


# NOTE: These are execution truth tables (WMS-facing) but live in the Inventory module
# so there is one inventory truth in the database.

class Site(Base, HasId, HasCreatedAt):
    __tablename__ = "inv_site"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_site_tenant_code", Site.tenant_id, Site.code)

class WMSLocation(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_location"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("inv_site.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), default="BIN", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class WMSLot(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_lot"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("wms_lot.id"), nullable=True, index=True)
    lot_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    supplier_lot: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    mfg_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    item: Mapped[InventoryItem] = relationship()

Index("ix_lot_tenant_item_lot", WMSLot.tenant_id, WMSLot.item_id, WMSLot.lot_number)

class WMSHandlingUnit(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_handling_unit"
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class InventoryBalance(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_inventory_balance"
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("wms_lot.id"), nullable=True, index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("wms_location.id"), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("wms_lot.id"), nullable=True, index=True)
    handling_unit_id: Mapped[str | None] = mapped_column(ForeignKey("wms_handling_unit.id"), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(24), default="AVAILABLE", nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_balance_item_loc_state", InventoryBalance.item_id, InventoryBalance.location_id, InventoryBalance.state)

class InventoryTxn(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_inventory_txn"
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    txn_type: Mapped[str] = mapped_column(String(32), default="MOVE", nullable=False, index=True)  # MOVE|RECEIPT|ISSUE_TO_WIP|RECEIPT_FROM_WIP|ADJUST
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("wms_lot.id"), nullable=True, index=True)
    from_location_id: Mapped[str | None] = mapped_column(ForeignKey("wms_location.id"), nullable=True, index=True)
    to_location_id: Mapped[str | None] = mapped_column(ForeignKey("wms_location.id"), nullable=True, index=True)
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("wms_lot.id"), nullable=True, index=True)
    handling_unit_id: Mapped[str | None] = mapped_column(ForeignKey("wms_handling_unit.id"), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(24), default="AVAILABLE", nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18,6), nullable=True)
    ext_cost: Mapped[Decimal | None] = mapped_column(Numeric(18,6), nullable=True)
    uom: Mapped[str] = mapped_column(String(16), default="EA", nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_txn_corr_item", InventoryTxn.correlation_id, InventoryTxn.item_id)


class InventorySerial(Base, HasId, HasCreatedAt):
    __tablename__ = "inv_serial"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("wms_lot.id"), nullable=True, index=True)
    serial_number: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    udi: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)  # UDI compliance (raw scan)
    udi_di: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    mfg_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="AVAILABLE", nullable=False, index=True)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("wms_location.id"), nullable=True, index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_serial_item_serial", InventorySerial.item_id, InventorySerial.serial_number)
Index("ix_serial_item_lot_serial", InventorySerial.item_id, InventorySerial.lot_id, InventorySerial.serial_number)


# ===== WIP Valuation (MES -> Inventory truth) =====

class WIPBalance(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_wip_balance"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    production_order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # mes_production_order.id
    fg_item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("wms_lot.id"), nullable=True, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_wip_po_item", WIPBalance.production_order_id, WIPBalance.fg_item_id)

class WIPTxn(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_wip_txn"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    production_order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    txn_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # MAT_ISSUE|LABOR|SCRAP|FG_RECEIPT|ADJUST
    item_id: Mapped[str | None] = mapped_column(ForeignKey("inv_item_master.id"), nullable=True, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    ext_cost: Mapped[Decimal] = mapped_column(Numeric(18,6), default=0, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_wip_txn_po_type", WIPTxn.production_order_id, WIPTxn.txn_type)
