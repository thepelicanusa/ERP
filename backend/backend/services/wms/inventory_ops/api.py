from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal
from app.db.models.inventory_exec import Item, Location, InventoryBalance, HandlingUnit

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.get("/balances")
def list_balances(db: Session = Depends(get_db), p=Depends(get_principal)):
    rows = db.query(InventoryBalance).all()
    return [{
        "item_id": r.item_id,
        "sku": r.item.sku,
        "location_code": r.location.code,
        "state": r.state,
        "qty": float(r.qty),
        "lot_id": r.lot_id,
    } for r in rows]

@router.post("/items")
def create_item(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    item = Item(sku=payload["sku"], description=payload.get("description"), tracking=payload.get("tracking","none"))
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "sku": item.sku}

@router.get("/items")
def list_items(db: Session = Depends(get_db), p=Depends(get_principal)):
    items = db.query(Item).order_by(Item.sku.asc()).all()
    return [{"id": i.id, "sku": i.sku, "description": i.description, "tracking": i.tracking} for i in items]

@router.post("/locations")
def create_location(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    loc = Location(code=payload["code"], type=payload.get("type","BIN"), zone=payload.get("zone"), capacity_units=payload.get("capacity_units"))
    db.add(loc); db.commit(); db.refresh(loc)
    return {"id": loc.id, "code": loc.code}

@router.get("/locations")
def list_locations(db: Session = Depends(get_db), p=Depends(get_principal)):
    locs = db.query(Location).order_by(Location.code.asc()).all()
    return [{"id": l.id, "code": l.code, "type": l.type, "zone": l.zone} for l in locs]


@router.post('/handling-units')
def create_hu(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    hu = HandlingUnit(lpn=payload['lpn'], type=payload.get('type','CARTON'), status=payload.get('status','OPEN'))
    if payload.get('location_code'):
        loc = db.query(Location).filter(Location.code == payload['location_code']).first()
        if loc:
            hu.location_id = loc.id
    db.add(hu); db.commit(); db.refresh(hu)
    return {'id': hu.id, 'lpn': hu.lpn, 'status': hu.status}

@router.get('/handling-units')
def list_hu(db: Session = Depends(get_db), p=Depends(get_principal)):
    rows = db.query(HandlingUnit).order_by(HandlingUnit.created_at.desc()).limit(200).all()
    return [{'id': h.id, 'lpn': h.lpn, 'type': h.type, 'status': h.status, 'location_code': (h.location.code if h.location else None)} for h in rows]
