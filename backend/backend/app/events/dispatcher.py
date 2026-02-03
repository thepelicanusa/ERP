from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.events.outbox import OutboxEvent
from app.events.subscriptions import EventSubscription


def _pattern_matches(pattern: str, topic: str) -> bool:
    """Very small pattern helper.

    Supported:
      - exact match
      - prefix match using trailing '.'
      - wildcard 'prefix.*' treated as prefix match
    """
    if not pattern:
        return False
    if pattern == topic:
        return True
    if pattern.endswith(".*"):
        return topic.startswith(pattern[:-1])  # keep trailing '.'
    if pattern.endswith("."):
        return topic.startswith(pattern)
    return False


def _get_matching_subs(db: Session, topic: str) -> list[EventSubscription]:
    subs = db.query(EventSubscription).filter(EventSubscription.is_active == True).all()  # noqa: E712
    return [s for s in subs if _pattern_matches(s.topic_pattern, topic)]


async def _deliver_one(client: httpx.AsyncClient, sub: EventSubscription, evt: OutboxEvent) -> tuple[bool, str | None]:
    headers = {k: str(v) for k, v in (sub.headers or {}).items()}
    body = {
        "topic": evt.topic,
        "event_id": evt.id,
        "created_at": evt.created_at.isoformat() if evt.created_at else None,
        "payload": evt.payload or {},
    }
    try:
        resp = await client.post(sub.target_url, json=body, headers=headers, timeout=10.0)
        if 200 <= resp.status_code < 300:
            return True, None
        return False, f"HTTP {resp.status_code}: {resp.text[:300]}"
    except Exception as e:
        return False, str(e)


def _schedule_next(attempt_count: int) -> datetime:
    # Simple exponential backoff capped at 10 minutes
    seconds = min(600, 2 ** min(attempt_count, 9))
    return datetime.utcnow() + timedelta(seconds=seconds)


async def run_dispatcher_forever(*, poll_interval_seconds: float = 1.0) -> None:
    """Background worker that delivers outbox events to webhook subscribers.

    This is a stub-by-design: good enough to prove the platform contracts,
    while keeping the implementation swappable for Kafka/NATS later.
    """
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await _dispatch_batch(client)
            except Exception:
                # Never crash the server because the dispatcher had a bad day
                pass
            await asyncio.sleep(poll_interval_seconds)


async def _dispatch_batch(client: httpx.AsyncClient) -> None:
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        events = (
            db.query(OutboxEvent)
            .filter(OutboxEvent.delivered == False)  # noqa: E712
            .filter(OutboxEvent.available_at <= now)
            .order_by(OutboxEvent.created_at.asc())
            .limit(50)
            .all()
        )
        if not events:
            return

        for evt in events:
            subs = _get_matching_subs(db, evt.topic)
            if not subs:
                # Nobody cares; mark delivered to avoid infinite growth
                evt.delivered = True
                evt.delivered_at = datetime.utcnow()
                continue

            # Deliver to all subs; event considered delivered when all succeed
            all_ok = True
            last_err = None
            for sub in subs:
                ok, err = await _deliver_one(client, sub, evt)
                if ok:
                    sub.last_error = None
                    sub.failure_count = 0
                    sub.last_delivered_at = datetime.utcnow()
                else:
                    all_ok = False
                    last_err = err
                    sub.last_error = err
                    sub.failure_count = (sub.failure_count or 0) + 1

            if all_ok:
                evt.delivered = True
                evt.delivered_at = datetime.utcnow()
                evt.last_error = None
            else:
                evt.attempt_count = (evt.attempt_count or 0) + 1
                evt.last_error = last_err
                evt.available_at = _schedule_next(evt.attempt_count)

        db.commit()
    finally:
        db.close()
