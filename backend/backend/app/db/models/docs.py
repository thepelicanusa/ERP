from __future__ import annotations
from sqlalchemy import String, DateTime, JSON, ForeignKey, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal

from app.db.base import Base
from app.db.models.wms.common import HasId, HasCreatedAt

class Receipt(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_receipt"
    ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class ReceiptLine(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_receipt_line"
    receipt_id: Mapped[str] = mapped_column(ForeignKey("wms_receipt.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    receipt: Mapped[Receipt] = relationship()
    item = relationship("app.db.models.inventory.InventoryItem")

class Order(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_order"
    ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class OrderLine(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_order_line"
    order_id: Mapped[str] = mapped_column(ForeignKey("wms_order.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    order: Mapped[Order] = relationship()
    item = relationship("app.db.models.inventory.InventoryItem")

class CountDoc(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_count"
    ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_receipt_ref", Receipt.ref)
Index("ix_order_ref", Order.ref)
Index("ix_count_ref", CountDoc.ref)

# ============================================================================
# Backward compatibility exports (WMS / API import stability)
# ============================================================================
# WMS tasking expects inbound/outbound naming.
InboundReceipt = Receipt
InboundReceiptLine = ReceiptLine

OutboundOrder = Order
OutboundOrderLine = OrderLine

# Cycle count naming
CycleCountRequest = CountDoc
CycleCountLine = None  # No line model exists yet; placeholder to satisfy imports

