from __future__ import annotations
from sqlalchemy import String, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from app.db.models.wms.common import HasId, HasCreatedAt

class SessionHandoff(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_session_handoff"
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    barcode: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    issued_by: Mapped[str] = mapped_column(String(128), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

Index("ix_handoff_session_used", SessionHandoff.session_id, SessionHandoff.used)
