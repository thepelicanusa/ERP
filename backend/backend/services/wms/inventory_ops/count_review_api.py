from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.session import get_db
from app.core.security import get_principal
from app.core.audit import AuditLog
from app.db.models.wms.counting import CountSubmission
from app.db.models.inventory_exec import Item, Location
from services.wms.inventory_ops.service import apply_movement
from app.events.outbox import OutboxEvent

router = APIRouter(prefix="/counts", tags=["counts-review"])

@router.get("/submissions")
def list_submissions(status: str = "PENDING_REVIEW", db: Session = Depends(get_db), p=Depends(get_principal)):
    rows = (db.query(CountSubmission)
            .filter(CountSubmission.status == status)
            .order_by(CountSubmission.created_at.desc())
            .limit(200).all())
    return [{
        "id": s.id,
        "task_id": s.task_id,
        "location_code": s.location.code,
        "sku": s.item.sku,
        "counted_qty": float(s.counted_qty),
        "expected_qty": float(s.expected_qty),
        "variance_qty": float(s.variance_qty),
        "status": s.status,
    } for s in rows]

@router.post("/submissions/{submission_id}/approve")
def approve(submission_id: str, payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    s = db.query(CountSubmission).filter(CountSubmission.id == submission_id).first()
    if not s:
        raise HTTPException(404, "Submission not found")
    if s.status != "PENDING_REVIEW":
        return {"ok": True, "status": s.status}

    # Apply adjustment movement to make balance match counted qty (AVAILABLE state only)
    variance = float(s.variance_qty)
    if abs(variance) > 0.000001:
        item = db.query(Item).filter(Item.id == s.item_id).first()
        loc = db.query(Location).filter(Location.id == s.location_id).first()
        if variance > 0:
            apply_movement(db, correlation_id=f"count-adjust:{s.id}", item=item, qty=variance, from_location=None, to_location=loc, actor=p.username, reason=payload.get("reason"))
        else:
            apply_movement(db, correlation_id=f"count-adjust:{s.id}", item=item, qty=abs(variance), from_location=loc, to_location=None, actor=p.username, reason=payload.get("reason"))

    s.status = "APPROVED"
    s.reviewed_by = p.username
    s.reviewed_at = datetime.utcnow()
    s.reason = payload.get("reason")

    db.add(AuditLog(actor=p.username, action="APPROVE_COUNT_ADJUSTMENT", entity_type="CountSubmission", entity_id=s.id, reason=s.reason, data={"variance": variance}))
    db.add(OutboxEvent(topic="CountAdjustmentApproved", payload={"submission_id": s.id, "variance": variance, "reviewed_by": p.username}))
    db.commit()
    return {"ok": True, "status": s.status}
