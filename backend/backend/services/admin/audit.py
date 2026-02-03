from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models.security_audit import AuditLog

def audit(db: Session, *, tenant_id: str, actor: str, action: str, entity_type: str, entity_id: str | None, payload: dict) -> None:
    db.add(AuditLog(tenant_id=tenant_id, actor=actor, action=action, entity_type=entity_type, entity_id=entity_id, payload=payload))
    db.commit()
