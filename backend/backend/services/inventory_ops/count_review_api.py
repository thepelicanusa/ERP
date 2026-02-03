from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from app.db.session import get_db
from app.db.models.wms.common import HasId, HasCreatedAt
from app.db.models.wms.counting import CountSubmission



# ============================================================================
# Router export (boot stability)
# ============================================================================
router = APIRouter(prefix="/inventory/counts", tags=["inventory-counts"])

@router.get("/health")
def health():
    return {"ok": True}

@router.get("/submissions")
def list_submissions(status: str = "PENDING_REVIEW", limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(CountSubmission)
    if status:
        q = q.filter(CountSubmission.status == status)
    rows = q.order_by(CountSubmission.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "location_id": r.location_id,
            "item_id": r.item_id,
            "counted_qty": float(r.counted_qty),
            "expected_qty": float(r.expected_qty),
            "variance_qty": float(r.variance_qty),
            "status": r.status,
        }
        for r in rows
    ]



