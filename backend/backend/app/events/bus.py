from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.events.outbox import OutboxEvent


def publish(db: Session, topic: str, payload: dict, *, available_at: datetime | None = None) -> OutboxEvent:
    """Publish an event by writing to the transactional outbox.

    This keeps modules decoupled and makes event delivery retryable.
    """
    evt = OutboxEvent(
        topic=topic,
        payload=payload or {},
        available_at=available_at or datetime.utcnow(),
        delivered=False,
        attempt_count=0,
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt
