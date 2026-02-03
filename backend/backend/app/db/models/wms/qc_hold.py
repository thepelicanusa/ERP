from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.models.wms.common import HasId, HasCreatedAt

class QCHold(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_qc_hold"
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # TASK, BALANCE, RECEIPT, ORDER
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="HOLD", nullable=False, index=True)  # HOLD/RELEASED
    hold_reason: Mapped[str] = mapped_column(String(512), nullable=False)
    held_by: Mapped[str] = mapped_column(String(128), nullable=False)
    released_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_qc_hold_entity", QCHold.entity_type, QCHold.entity_id)
