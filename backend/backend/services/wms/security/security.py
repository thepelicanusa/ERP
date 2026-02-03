from __future__ import annotations
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.db.models.wms.controls import UserRole, ApprovalRule

def has_role(db: Session, username: str, role: str) -> bool:
    return db.query(UserRole).filter(UserRole.username == username, UserRole.role == role, UserRole.is_active == True).first() is not None

def require_approval(db: Session, *, entity_type: str, action: str, actor: str, created_by: str | None):
    rule = db.query(ApprovalRule).filter(ApprovalRule.entity_type == entity_type, ApprovalRule.action == action).first()
    if not rule:
        return  # no rule -> allowed
    if rule.no_self_approve and created_by and created_by == actor:
        raise HTTPException(403, f"Self-approval blocked by policy for {entity_type}.{action}")
    if not has_role(db, actor, rule.required_role):
        raise HTTPException(403, f"Role {rule.required_role} required for {entity_type}.{action}")
