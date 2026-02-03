from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.wms.common import HasCreatedAt, HasId


class EventSubscription(Base, HasId, HasCreatedAt):
    """Webhook subscription for the platform event bus.

    Modules can register a webhook URL for a given topic (or prefix pattern).
    The dispatcher will POST the event payload to the target URL.

    Patterns:
      - exact match:   "inventory.lot.received"
      - prefix match:  "inventory." (recommended)
      - wildcard:      "inventory.*" (treated as prefix)
    """

    __tablename__ = "event_subscription"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    topic_pattern: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    headers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index("ix_event_sub_active", EventSubscription.is_active, EventSubscription.topic_pattern)
