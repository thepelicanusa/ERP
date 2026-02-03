from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_principal
from app.core.tenant import get_tenant_id
from app.db.models.planning import Forecast, PlannedOrder, MRPNettingRun

router = APIRouter(prefix="/planning", tags=["planning"])

@router.get("/health")
def health():
    return {"ok": True, "service": "planning"}

@router.get("/forecasts")
def list_forecasts(item_id: Optional[str] = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    tenant_id = get_tenant_id()
    q = db.query(Forecast).filter(Forecast.tenant_id == tenant_id)
    if item_id:
        q = q.filter(Forecast.item_id == item_id)
    rows = q.order_by(Forecast.period_start.desc()).limit(500).all()
    return [{
        "id": r.id,
        "item_id": r.item_id,
        "period_start": r.period_start,
        "period_type": r.period_type,
        "qty": float(r.qty),
        "meta": r.meta or {},
        "created_at": r.created_at,
    } for r in rows]

@router.post("/forecasts")
def upsert_forecast(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    """
    Simple forecast upsert (MVP).
    Required: item_id, period_start (YYYY-MM-DD), qty
    Optional: period_type, meta
    """
    tenant_id = get_tenant_id()
    try:
        period_start = date.fromisoformat(payload["period_start"])
        qty = payload["qty"]
        item_id = payload["item_id"]
    except Exception as e:
        raise HTTPException(400, f"Invalid payload: {e}")

    period_type = payload.get("period_type", "WEEK")
    meta = payload.get("meta", {}) or {}

    row = db.query(Forecast).filter(
        Forecast.tenant_id == tenant_id,
        Forecast.item_id == item_id,
        Forecast.period_start == period_start,
        Forecast.period_type == period_type,
    ).first()
    if not row:
        row = Forecast(
            tenant_id=tenant_id,
            item_id=item_id,
            period_start=period_start,
            period_type=period_type,
            qty=qty,
            meta=meta,
        )
        db.add(row)
    else:
        row.qty = qty
        row.meta = meta
    db.commit()
    return {"ok": True, "id": row.id}

@router.get("/planned-orders")
def list_planned_orders(status: Optional[str] = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    tenant_id = get_tenant_id()
    q = db.query(PlannedOrder).filter(PlannedOrder.tenant_id == tenant_id)
    if status:
        q = q.filter(PlannedOrder.status == status)
    rows = q.order_by(PlannedOrder.due_date.asc()).limit(500).all()
    return [{
        "id": r.id,
        "order_type": r.order_type,
        "item_id": r.item_id,
        "due_date": r.due_date,
        "qty": float(r.qty),
        "status": r.status,
        "source": r.source,
        "meta": r.meta or {},
        "created_at": r.created_at,
    } for r in rows]

@router.post("/mrp/runs")
def record_mrp_run(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    """
    Records an MRP netting run summary (MVP). In the full platform, the MRP engine publishes events.
    """
    tenant_id = get_tenant_id()
    row = MRPNettingRun(
        tenant_id=tenant_id,
        status=payload.get("status", "DONE"),
        params=payload.get("params", {}) or {},
        results=payload.get("results", {}) or {},
    )
    db.add(row)
    db.commit()
    return {"ok": True, "id": row.id}
