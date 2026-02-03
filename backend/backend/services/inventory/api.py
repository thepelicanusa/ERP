from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.inventory import InventoryItem
from app.db.models.inventory_exec import InventoryTxn
import uuid

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.get("/items")
def list_items(db: Session = Depends(get_db), limit: int = 200):
    qs = db.query(ItemMaster).order_by(ItemMaster.created_at.desc()).limit(limit).all()
    return [{"id": i.id, "sku": i.sku, "name": i.item_name, "uom": i.base_uom} for i in qs]

@router.post("/items")
def create_item(payload: dict, db: Session = Depends(get_db)):
    sku = payload.get("sku") or str(uuid.uuid4())
    i = ItemMaster(
        sku=sku,
        item_name=payload.get("item_name") or payload.get("name") or sku,
        base_uom=payload.get("base_uom") or "EA",
        item_type=payload.get("item_type") or "FG",
        status=payload.get("status") or "ACTIVE",
        meta=payload.get("meta") or {},
    )
    db.add(i); db.commit(); db.refresh(i)
    return {"id": i.id, "sku": i.sku}

@router.get("/items/{item_id}")
def get_item(item_id: str, db: Session = Depends(get_db)):
    i = db.query(ItemMaster).filter(ItemMaster.id == item_id).first()
    if not i:
        raise HTTPException(404, "Item not found")
    return {"id": i.id, "sku": i.sku, "item_name": i.item_name, "meta": i.meta}

@router.get("/health")
def health():
    return {"ok": True}
