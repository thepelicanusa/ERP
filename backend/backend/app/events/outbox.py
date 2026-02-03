from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.wms.common import HasCreatedAt, HasId


class OutboxEvent(Base, HasId, HasCreatedAt):
    """Transactional outbox.

    This is intentionally simple: other modules can publish events by inserting rows.
    A background dispatcher (see app.events.dispatcher) delivers events to registered
    webhook subscriptions.
    """

    __tablename__ = "outbox_event"

    topic: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Delivery state (webhook dispatcher)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index("ix_outbox_topic_created", OutboxEvent.topic, OutboxEvent.created_at)
Index("ix_outbox_delivery", OutboxEvent.delivered, OutboxEvent.available_at)
