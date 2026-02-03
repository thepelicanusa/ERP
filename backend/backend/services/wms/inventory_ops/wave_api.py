from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal
from app.db.models.planning import Wave, WaveOrder
from services.wms.inventory_ops.wave_service import create_wave, release_wave

router = APIRouter(prefix="/waves", tags=["waves"])

@router.post("")
def create(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    code = payload.get("code") or f"WAVE-{p.username}-001"
    order_ids = payload.get("order_ids") or []
    wv = create_wave(db, code=code, created_by=p.username, order_ids=order_ids)
    return {"id": wv.id, "code": wv.code, "status": wv.status}

@router.get("")
def list_waves(db: Session = Depends(get_db), p=Depends(get_principal)):
    rows = db.query(Wave).order_by(Wave.created_at.desc()).limit(200).all()
    return [{"id": w.id, "code": w.code, "status": w.status} for w in rows]

@router.get("/{wave_id}")
def get_wave(wave_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    wv = db.query(Wave).filter(Wave.id == wave_id).first()
    if not wv:
        raise HTTPException(404, "Wave not found")
    orders = db.query(WaveOrder).filter(WaveOrder.wave_id == wave_id).all()
    return {"id": wv.id, "code": wv.code, "status": wv.status, "orders": [{"order_id": o.order_id, "status": o.status} for o in orders]}

@router.post("/{wave_id}/release")
def release(wave_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    try:
        wv = release_wave(db, wave_id=wave_id, actor=p.username)
        return {"id": wv.id, "status": wv.status}
    except ValueError as e:
        raise HTTPException(404, str(e))
