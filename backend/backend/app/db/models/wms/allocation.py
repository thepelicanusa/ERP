from __future__ import annotations
from sqlalchemy import String, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models.wms.common import HasId, HasCreatedAt

class Allocation(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_allocation"
    order_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    order_line_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("wms_location.id"), nullable=False, index=True)
    handling_unit_id: Mapped[str | None] = mapped_column(ForeignKey("wms_handling_unit.id"), nullable=True, index=True)
    qty: Mapped[float] = mapped_column(Numeric(18,6), nullable=False)

    item = relationship("app.db.models.inventory.InventoryItem")
    location = relationship("app.db.models.inventory_exec.WMSLocation")
    handling_unit = relationship("app.db.models.inventory_exec.WMSHandlingUnit")

Index("ix_wms_alloc_order_line_item", Allocation.order_id, Allocation.order_line_id, Allocation.item_id)

