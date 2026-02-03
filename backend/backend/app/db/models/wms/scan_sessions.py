from __future__ import annotations
from sqlalchemy import String, DateTime, JSON, ForeignKey, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from app.db.models.wms.common import HasId, HasCreatedAt

class MesScanSession(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_scan_session"
    mode: Mapped[str] = mapped_column(String(32), nullable=False)  # START_OP|ISSUE|RECEIVE|QC
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)  # ACTIVE|COMPLETED|CANCELLED
    expected_next_scan: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    hard_lock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expected: Mapped[str] = mapped_column(String(32), nullable=False)  # MO|OP|ITEM|LOC|QTY|CHECK
    operator: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class MesScanEvent(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_scan_event"
    session_id: Mapped[str] = mapped_column(ForeignKey("mes_scan_session.id"), nullable=False, index=True)
    raw: Mapped[str] = mapped_column(String(256), nullable=False)
    parsed: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[str] = mapped_column(String(24), nullable=False)  # OK|REJECTED
    message: Mapped[str | None] = mapped_column(String(256), nullable=True)
    new_expected: Mapped[str | None] = mapped_column(String(32), nullable=True)

Index("ix_mes_scan_event_session_created", MesScanEvent.session_id, MesScanEvent.created_at)

# ============================================================================
# Backward compatibility exports (WMS API import stability)
# ============================================================================
# Some WMS endpoints import ScanSession/ScanEvent from this module.
ScanSession = MesScanSession
ScanEvent = MesScanEvent

