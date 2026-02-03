from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt

class FinPeriodClose(Base, HasId, HasCreatedAt):
    __tablename__ = "fin_period_close"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False, index=True)  # OPEN/CLOSED
    closed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_fin_close_tenant_period", FinPeriodClose.tenant_id, FinPeriodClose.period)
