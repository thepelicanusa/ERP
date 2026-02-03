from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal
from app.db.models.inventory_exec import HandlingUnit
from app.events.outbox import OutboxEvent

router = APIRouter(prefix="/shipping", tags=["shipping"])

@router.post("/close-lpn/{hu_id}")
def close_lpn(hu_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    hu = db.query(HandlingUnit).filter(HandlingUnit.id == hu_id).first()
    hu.status = "CLOSED"
    db.add(OutboxEvent(topic="LPNClosed", payload={"hu_id": hu_id}))
    db.commit()
    return {"ok": True}

@router.post("/ship-lpn/{hu_id}")
def ship_lpn(hu_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    hu = db.query(HandlingUnit).filter(HandlingUnit.id == hu_id).first()
    hu.status = "SHIPPED"
    db.add(OutboxEvent(topic="LPNShipped", payload={"hu_id": hu_id}))
    db.commit()
    return {"ok": True}
