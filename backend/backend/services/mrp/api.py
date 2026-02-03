from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.mrp import BOM, BOMLine, Routing, RoutingOperation, WorkCenter
import uuid
from decimal import Decimal

router = APIRouter(prefix="/mrp", tags=["mrp"])

@router.get("/work-centers")
def list_wcs(db: Session = Depends(get_db), limit: int = 200):
    ws = db.query(WorkCenter).order_by(WorkCenter.created_at.desc()).limit(limit).all()
    return [{"id": w.id, "code": w.work_center_code, "name": w.work_center_name} for w in ws]

@router.post("/work-centers")
def create_wc(payload: dict, db: Session = Depends(get_db)):
    code = payload.get("work_center_code") or payload.get("code") or f"WC-{str(uuid.uuid4())[:6].upper()}"
    w = WorkCenter(work_center_code=code, work_center_name=payload.get("work_center_name") or payload.get("name") or code, status="ACTIVE", meta={})
    db.add(w); db.commit(); db.refresh(w)
    return {"id": w.id, "code": w.work_center_code}

@router.post("/boms")
def create_bom(payload: dict, db: Session = Depends(get_db)):
    parent_item_id = payload.get("parent_item_id")
    if not parent_item_id:
        raise HTTPException(400, "parent_item_id required")
    b = BOM(bom_code=payload.get("bom_code") or f"BOM-{str(uuid.uuid4())[:8].upper()}",
            parent_item_id=parent_item_id, revision=payload.get("revision") or "A", status="ACTIVE", meta={})
    db.add(b); db.commit(); db.refresh(b)
    for ln in (payload.get("lines") or []):
        db.add(BOMLine(bom_id=b.id, component_item_id=ln["component_item_id"], quantity=Decimal(str(ln.get("quantity") or 0)), uom=ln.get("uom") or "EA", meta={}))
    db.commit()
    return {"id": b.id, "bom_code": b.bom_code}

@router.get("/health")
def health():
    return {"ok": True}
