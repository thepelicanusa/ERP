from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal
from services.wms.inventory_ops.wave_optimizer import optimize_wave

router = APIRouter(prefix="/waves", tags=["waves-optimization"])

@router.get("/{wave_id}/optimize")
def optimize(wave_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    return optimize_wave(db, wave_id)
