from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal
from app.db.models.wms.short_pick import ShortPick
from app.events.outbox import OutboxEvent

router = APIRouter(prefix="/short-picks", tags=["short-picks"])

@router.post("/")
def create_short_pick(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    sp = ShortPick(**payload)
    db.add(sp)
    db.add(OutboxEvent(topic="ShortPickCreated", payload=payload))
    db.commit()
    return {"id": sp.id}

@router.post("/{short_pick_id}/resolve")
def resolve_short_pick(short_pick_id: str, payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    sp = db.query(ShortPick).filter(ShortPick.id == short_pick_id).first()
    sp.resolution = payload["resolution"]
    db.add(OutboxEvent(topic="ShortPickResolved", payload={"id": sp.id, "resolution": sp.resolution}))
    db.commit()
    return {"ok": True}
