from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_principal
from app.db.session import get_db
from app.events import bus
from app.events.subscriptions import EventSubscription


router = APIRouter(prefix="/admin/events", tags=["admin_events"])


def _require_admin(principal) -> None:
    roles = set(getattr(principal, "roles", []) or [])
    if "ADMIN" not in roles:
        raise HTTPException(403, "ADMIN role required")


@router.get("/subscriptions")
def list_subscriptions(db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    subs = db.query(EventSubscription).order_by(EventSubscription.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "topic_pattern": s.topic_pattern,
            "target_url": s.target_url,
            "headers": s.headers or {},
            "is_active": bool(s.is_active),
            "failure_count": int(s.failure_count or 0),
            "last_error": s.last_error,
            "last_delivered_at": s.last_delivered_at.isoformat() if s.last_delivered_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in subs
    ]


@router.post("/subscriptions")
def create_subscription(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    name = (payload or {}).get("name") or "subscription"
    topic_pattern = (payload or {}).get("topic_pattern")
    target_url = (payload or {}).get("target_url")
    headers = (payload or {}).get("headers") or {}

    if not topic_pattern or not target_url:
        raise HTTPException(422, "topic_pattern and target_url are required")

    s = EventSubscription(
        name=name,
        topic_pattern=str(topic_pattern),
        target_url=str(target_url),
        headers=headers,
        is_active=bool((payload or {}).get("is_active", True)),
        last_error=None,
        failure_count=0,
        last_delivered_at=None,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"ok": True, "id": s.id}


@router.post("/subscriptions/{sub_id}/toggle")
def toggle_subscription(sub_id: str, payload: dict | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    s = db.query(EventSubscription).filter(EventSubscription.id == sub_id).first()
    if not s:
        raise HTTPException(404, "Unknown subscription")
    s.is_active = bool((payload or {}).get("is_active", not bool(s.is_active)))
    db.commit()
    return {"ok": True, "id": s.id, "is_active": bool(s.is_active)}


@router.delete("/subscriptions/{sub_id}")
def delete_subscription(sub_id: str, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    s = db.query(EventSubscription).filter(EventSubscription.id == sub_id).first()
    if not s:
        return {"ok": True, "deleted": False}
    db.delete(s)
    db.commit()
    return {"ok": True, "deleted": True}


@router.post("/publish")
def publish_event(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    """Admin-only test publish endpoint.

    Production modules should publish by calling app.events.bus.publish(db, topic, payload)
    inside their own transaction boundary.
    """
    _require_admin(principal)
    topic = (payload or {}).get("topic")
    event_payload = (payload or {}).get("payload") or {}
    if not topic:
        raise HTTPException(422, "topic is required")
    evt = bus.publish(db, str(topic), dict(event_payload), available_at=datetime.utcnow())
    return {"ok": True, "event_id": evt.id, "topic": evt.topic}
