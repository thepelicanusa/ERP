from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_principal
from app.db.session import get_db
from app.db.models.support import SupportTicket, SupportTicketComment, TicketPriority, TicketStatus

router = APIRouter(prefix="/support", tags=["support"])

def _tenant_id() -> str:
    return "default"

@router.post("/tickets")
def create_ticket(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    party_profile_id = payload.get("party_profile_id")
    if not party_profile_id:
        raise HTTPException(400, "party_profile_id is required")

    sla_hours = payload.get("sla_hours")
    sla_due_at = None
    if isinstance(sla_hours, (int, float)) and sla_hours > 0:
        sla_due_at = datetime.utcnow() + timedelta(hours=float(sla_hours))

    t = SupportTicket(
        id=str(uuid.uuid4()),
        tenant_id=_tenant_id(),
        legal_entity_id=payload.get("legal_entity_id"),
        party_profile_id=party_profile_id,
        title=payload.get("title") or "Untitled",
        description=payload.get("description"),
        status=TicketStatus.OPEN,
        priority=TicketPriority(payload.get("priority") or "MEDIUM"),
        assigned_user_id=payload.get("assigned_user_id"),
        sla_due_at=sla_due_at,
    )
    db.add(t); db.commit()
    return {"id": t.id, "status": t.status.value, "priority": t.priority.value}

@router.get("/tickets")
def list_tickets(party_profile_id: str | None = None, status: str | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    q = db.query(SupportTicket).filter(SupportTicket.tenant_id==_tenant_id())
    if party_profile_id:
        q = q.filter(SupportTicket.party_profile_id==party_profile_id)
    if status and status in [s.value for s in TicketStatus]:
        q = q.filter(SupportTicket.status==TicketStatus(status))
    rows = q.order_by(SupportTicket.created_at.desc()).limit(100).all()
    return [{
        "id": r.id,
        "party_profile_id": r.party_profile_id,
        "title": r.title,
        "status": r.status.value,
        "priority": r.priority.value,
        "sla_due_at": r.sla_due_at.isoformat() if r.sla_due_at else None,
        "created_at": r.created_at.isoformat(),
    } for r in rows]

@router.post("/tickets/{ticket_id}/comments")
def add_comment(ticket_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    body = payload.get("body") or ""
    if not body.strip():
        raise HTTPException(400, "body is required")
    t = db.query(SupportTicket).filter(SupportTicket.tenant_id==_tenant_id(), SupportTicket.id==ticket_id).first()
    if not t:
        raise HTTPException(404, "ticket not found")
    c = SupportTicketComment(ticket_id=ticket_id, author_user_id=getattr(principal,"username",None), body=body.strip())
    db.add(c); db.commit()
    return {"ok": True, "comment_id": c.id}
