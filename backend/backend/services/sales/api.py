from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.sales import Customer, SalesQuote, SalesQuoteLine, SalesOrder, SalesOrderLine
import uuid
from decimal import Decimal

router = APIRouter(prefix="/sales", tags=["sales"])

@router.get("/customers")
def list_customers(db: Session = Depends(get_db), limit: int = 200):
    cs = db.query(Customer).order_by(Customer.created_at.desc()).limit(limit).all()
    return [{"id": c.id, "code": c.customer_code, "name": c.customer_name} for c in cs]

@router.post("/customers")
def create_customer(payload: dict, db: Session = Depends(get_db)):
    code = payload.get("customer_code") or payload.get("code") or str(uuid.uuid4())[:8].upper()
    c = Customer(customer_code=code, customer_name=payload.get("customer_name") or payload.get("name") or code, meta=payload.get("meta") or {})
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "code": c.customer_code}

@router.post("/quotes")
def create_quote(payload: dict, db: Session = Depends(get_db)):
    customer_id = payload.get("customer_id")
    if not customer_id:
        raise HTTPException(400, "customer_id required")
    from datetime import date, timedelta
    q = SalesQuote(quote_number=payload.get("quote_number") or f"Q-{str(uuid.uuid4())[:8].upper()}", customer_id=customer_id, status="DRAFT", currency="USD", quote_date=payload.get("quote_date") or date.today(), expiry_date=payload.get("expiry_date") or (date.today() + timedelta(days=30)), meta={})
    db.add(q); db.commit(); db.refresh(q)
    for ln in (payload.get("lines") or []):
        db.add(SalesQuoteLine(quote_id=q.id, item_id=ln["item_id"], quantity=Decimal(str(ln.get("quantity") or 0)), unit_price=Decimal(str(ln.get("unit_price") or 0)), meta={}))
    db.commit()
    return {"id": q.id, "quote_number": q.quote_number}

@router.post("/orders")
def create_order(payload: dict, db: Session = Depends(get_db)):
    customer_id = payload.get("customer_id")
    if not customer_id:
        raise HTTPException(400, "customer_id required")
    from datetime import date
    o = SalesOrder(order_number=payload.get("order_number") or f"SO-{str(uuid.uuid4())[:8].upper()}", customer_id=customer_id, status="OPEN", currency="USD", order_date=payload.get("order_date") or date.today(), meta={})
    db.add(o); db.commit(); db.refresh(o)
    for ln in (payload.get("lines") or []):
        db.add(SalesOrderLine(order_id=o.id, item_id=ln["item_id"], quantity=Decimal(str(ln.get("quantity") or 0)), unit_price=Decimal(str(ln.get("unit_price") or 0)), meta={}))
    db.commit()
    return {"id": o.id, "order_number": o.order_number}

@router.get("/quotes")
def list_quotes(db: Session = Depends(get_db), limit: int = 200):
    qs = db.query(SalesQuote).order_by(SalesQuote.created_at.desc()).limit(limit).all()
    return [{"id": q.id, "quote_number": q.quote_number, "customer_id": q.customer_id, "status": q.status} for q in qs]

@router.get("/quotes/{quote_id}")
def get_quote(quote_id: str, db: Session = Depends(get_db)):
    q = db.query(SalesQuote).filter(SalesQuote.id == quote_id).first()
    if not q:
        raise HTTPException(404, "not found")
    lines = db.query(SalesQuoteLine).filter(SalesQuoteLine.quote_id == quote_id).all()
    return {
        "id": q.id,
        "quote_number": q.quote_number,
        "customer_id": q.customer_id,
        "status": q.status,
        "currency": q.currency,
        "lines": [{"id": ln.id, "item_id": ln.item_id, "quantity": float(ln.quantity), "unit_price": float(ln.unit_price)} for ln in lines],
    }

@router.get("/orders")
def list_orders(db: Session = Depends(get_db), limit: int = 200):
    os_ = db.query(SalesOrder).order_by(SalesOrder.created_at.desc()).limit(limit).all()
    return [{"id": o.id, "order_number": o.order_number, "customer_id": o.customer_id, "status": o.status} for o in os_]

@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    o = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "not found")
    lines = db.query(SalesOrderLine).filter(SalesOrderLine.order_id == order_id).all()
    return {
        "id": o.id,
        "order_number": o.order_number,
        "customer_id": o.customer_id,
        "status": o.status,
        "currency": o.currency,
        "lines": [{"id": ln.id, "item_id": ln.item_id, "quantity": float(ln.quantity), "unit_price": float(ln.unit_price)} for ln in lines],
    }

@router.get("/health")
def health():
    return {"ok": True}
