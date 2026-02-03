from __future__ import annotations
from sqlalchemy import String, Numeric, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.base import Base
from app.db.models.wms.common import HasId, HasCreatedAt

class CountSubmission(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_count_submission"
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("wms_location.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("inv_item_master.id"), nullable=False, index=True)
    counted_qty: Mapped[float] = mapped_column(Numeric(18,6), nullable=False)
    expected_qty: Mapped[float] = mapped_column(Numeric(18,6), nullable=False)
    variance_qty: Mapped[float] = mapped_column(Numeric(18,6), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING_REVIEW", nullable=False)  # PENDING_REVIEW|APPROVED|REJECTED
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    location = relationship("app.db.models.inventory_exec.WMSLocation")
    item = relationship("app.db.models.inventory.InventoryItem")

# appended via PowerShell
# example line
