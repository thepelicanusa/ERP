from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.qms import InspectionPlan, Inspection, InspectionResult
import uuid

router = APIRouter(prefix="/qms", tags=["qms"])

@router.get("/plans")
def list_plans(db: Session = Depends(get_db), limit: int = 200):
    ps = db.query(InspectionPlan).order_by(InspectionPlan.created_at.desc()).limit(limit).all()
    return [{"id": p.id, "code": p.plan_code, "name": p.plan_name, "status": p.status} for p in ps]

@router.post("/plans")
def create_plan(payload: dict, db: Session = Depends(get_db)):
    code = payload.get("plan_code") or payload.get("code") or f"IP-{str(uuid.uuid4())[:8].upper()}"
    p = InspectionPlan(plan_code=code, plan_name=payload.get("plan_name") or payload.get("name") or code, status="ACTIVE", meta={})
    db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id, "code": p.plan_code}

@router.post("/inspections")
def create_inspection(payload: dict, db: Session = Depends(get_db)):
    plan_id = payload.get("plan_id")
    if not plan_id:
        raise HTTPException(400, "plan_id required")
    ins = Inspection(inspection_number=payload.get("inspection_number") or f"INSP-{str(uuid.uuid4())[:8].upper()}",
                     plan_id=plan_id, status="OPEN", meta={})
    db.add(ins); db.commit(); db.refresh(ins)
    return {"id": ins.id, "inspection_number": ins.inspection_number}

@router.get("/health")
def health():
    return {"ok": True}
