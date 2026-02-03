from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.purchasing import Vendor, PurchaseOrder, PurchaseOrderLine
import uuid
from decimal import Decimal

router = APIRouter(prefix="/purchasing", tags=["purchasing"])

@router.get("/vendors")
def list_vendors(db: Session = Depends(get_db), limit: int = 200):
    vs = db.query(Vendor).order_by(Vendor.created_at.desc()).limit(limit).all()
    return [{"id": v.id, "code": v.vendor_code, "name": v.vendor_name} for v in vs]

@router.post("/vendors")
def create_vendor(payload: dict, db: Session = Depends(get_db)):
    code = payload.get("vendor_code") or payload.get("code") or str(uuid.uuid4())[:8].upper()
    v = Vendor(vendor_code=code, vendor_name=payload.get("vendor_name") or payload.get("name") or code, meta=payload.get("meta") or {})
    db.add(v); db.commit(); db.refresh(v)
    return {"id": v.id, "code": v.vendor_code}

@router.post("/purchase-orders")
def create_po(payload: dict, db: Session = Depends(get_db)):
    vendor_id = payload.get("vendor_id")
    if not vendor_id:
        raise HTTPException(400, "vendor_id required")
    from datetime import date
    po = PurchaseOrder(po_number=payload.get("po_number") or f"PO-{str(uuid.uuid4())[:8].upper()}", vendor_id=vendor_id, status="OPEN", currency="USD", po_date=payload.get("po_date") or date.today(), meta={})
    db.add(po); db.commit(); db.refresh(po)
    for ln in (payload.get("lines") or []):
        db.add(PurchaseOrderLine(purchase_order_id=po.id, item_id=ln["item_id"], quantity=Decimal(str(ln.get("quantity") or 0)), unit_price=Decimal(str(ln.get("unit_price") or 0)), meta={}))
    db.commit()
    return {"id": po.id, "po_number": po.po_number}

@router.get("/purchase-orders")
def list_purchase_orders(db: Session = Depends(get_db), limit: int = 200):
    pos = db.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).limit(limit).all()
    return [{"id": po.id, "po_number": po.po_number, "vendor_id": po.vendor_id, "status": po.status} for po in pos]

@router.get("/purchase-orders/{po_id}")
def get_purchase_order(po_id: str, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "not found")
    lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.purchase_order_id == po_id).all()
    return {
        "id": po.id,
        "po_number": po.po_number,
        "vendor_id": po.vendor_id,
        "status": po.status,
        "currency": po.currency,
        "lines": [{"id": ln.id, "item_id": ln.item_id, "quantity": float(ln.quantity), "unit_price": float(ln.unit_price)} for ln in lines],
    }

@router.get("/health")
def health():
    return {"ok": True}
