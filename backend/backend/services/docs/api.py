from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.docs import Receipt, ReceiptLine, Order, OrderLine, CountDoc
from app.db.models.inventory import InventoryItem
from decimal import Decimal
import uuid

router = APIRouter(prefix="/docs", tags=["docs"])

@router.post("/receipts")
def create_receipt(payload: dict, db: Session = Depends(get_db)):
    r = Receipt(ref=payload.get("ref") or str(uuid.uuid4()), status="OPEN", meta={})
    db.add(r); db.commit(); db.refresh(r)
    lines = payload.get("lines") or []
    for ln in lines:
        sku = ln.get("sku")
        qty = Decimal(str(ln.get("qty") or 0))
        item = db.query(InventoryItem).filter(InventoryItem.item_code == sku).first()
        if not item:
            item = InventoryItem(wms_item_id=sku, item_code=sku, description=sku, base_uom="EA", item_type="FINISHED_GOOD", is_active=True, meta={})
            db.add(item); db.flush()
        db.add(ReceiptLine(receipt_id=r.id, item_id=item.id, qty=qty, meta={}))
    db.commit()
    return {"id": r.id, "ref": r.ref}

@router.get("/receipts")
def list_receipts(db: Session = Depends(get_db)):
    rs = db.query(Receipt).order_by(Receipt.created_at.desc()).limit(50).all()
    return [{"id": r.id, "ref": r.ref, "status": r.status} for r in rs]

@router.post("/orders")
def create_order(payload: dict, db: Session = Depends(get_db)):
    o = Order(ref=payload.get("ref") or str(uuid.uuid4()), status="OPEN", meta={})
    db.add(o); db.commit(); db.refresh(o)
    lines = payload.get("lines") or []
    for ln in lines:
        sku = ln.get("sku")
        qty = Decimal(str(ln.get("qty") or 0))
        item = db.query(InventoryItem).filter(InventoryItem.item_code == sku).first()
        if not item:
            item = InventoryItem(wms_item_id=sku, item_code=sku, description=sku, base_uom="EA", item_type="FINISHED_GOOD", is_active=True, meta={})
            db.add(item); db.flush()
        db.add(OrderLine(order_id=o.id, item_id=item.id, qty=qty, meta={}))
    db.commit()
    return {"id": o.id, "ref": o.ref}

@router.get("/orders")
def list_orders(db: Session = Depends(get_db)):
    os_ = db.query(Order).order_by(Order.created_at.desc()).limit(50).all()
    return [{"id": o.id, "ref": o.ref, "status": o.status} for o in os_]

@router.post("/counts")
def create_count(payload: dict, db: Session = Depends(get_db)):
    c = CountDoc(ref=payload.get("ref") or str(uuid.uuid4()), status="OPEN", meta={"locations": payload.get("locations") or []})
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "ref": c.ref}

@router.get("/counts")
def list_counts(db: Session = Depends(get_db)):
    cs = db.query(CountDoc).order_by(CountDoc.created_at.desc()).limit(50).all()
    return [{"id": c.id, "ref": c.ref, "status": c.status} for c in cs]

# The following "generate tasks" endpoints are thin wrappers; task generation lives in services.wms.* already.
@router.post("/receipts/{receipt_id}/generate-tasks")
def gen_receipt_tasks(receipt_id: str, payload: dict, db: Session = Depends(get_db)):
    from services.wms.tasking.service import generate_receipt_tasks
    staging = payload.get("staging_location_code") or "STAGE"
    return generate_receipt_tasks(db, receipt_id=receipt_id, staging_location_code=staging)

@router.post("/orders/{order_id}/generate-tasks")
def gen_order_tasks(order_id: str, db: Session = Depends(get_db)):
    from services.wms.tasking.service import generate_order_tasks
    return generate_order_tasks(db, order_id=order_id)

@router.post("/counts/{count_id}/generate-tasks")
def gen_count_tasks(count_id: str, db: Session = Depends(get_db)):
    from services.wms.tasking.service import generate_count_tasks
    return generate_count_tasks(db, count_id=count_id)


