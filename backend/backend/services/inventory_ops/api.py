from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.inventory import InventoryItem
from app.db.models.inventory_exec import WMSLocation, InventoryBalance
import uuid

router = APIRouter(prefix="/inventory", tags=["inventory_wms"])

@router.get("/items")
def list_items(db: Session = Depends(get_db), limit: int = 200):
    items = db.query(InventoryItem).order_by(InventoryItem.created_at.desc()).limit(limit).all()
    return [{"id": i.id, "item_code": i.item_code, "description": i.description, "uom": i.base_uom} for i in items]

@router.post("/items")
def create_item(payload: dict, db: Session = Depends(get_db)):
    code = payload.get("item_code") or payload.get("code") or str(uuid.uuid4())[:8].upper()
    it = InventoryItem(
        wms_item_id=payload.get("wms_item_id") or code,
        item_code=code,
        description=payload.get("description") or payload.get("item_name") or code,
        base_uom=payload.get("base_uom") or "EA",
        item_type=payload.get("item_type") or "FINISHED_GOOD",
        is_active=True,
        meta=payload.get("meta") or {},
    )
    db.add(it); db.commit(); db.refresh(it)
    return {"id": it.id, "item_code": it.item_code}

@router.get("/locations")
def list_locations(db: Session = Depends(get_db), limit: int = 200):
    locs = db.query(WMSLocation).order_by(WMSLocation.created_at.desc()).limit(limit).all()
    return [{"id": l.id, "code": l.code, "type": l.type} for l in locs]

@router.post("/locations")
def create_location(payload: dict, db: Session = Depends(get_db)):
    code = payload.get("code")
    if not code:
        raise HTTPException(400, "code required")
    loc = WMSLocation(code=code, type=payload.get("type") or "BIN", meta=payload.get("meta") or {})
    db.add(loc); db.commit(); db.refresh(loc)
    return {"id": loc.id, "code": loc.code}

@router.get("/balances")
def list_balances(db: Session = Depends(get_db), limit: int = 200):
    bs = db.query(InventoryBalance).limit(limit).all()
    return [{"id": b.id, "item_id": b.item_id, "location_id": b.location_id, "qty": float(b.qty), "state": b.state} for b in bs]
