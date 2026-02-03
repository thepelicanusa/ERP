from __future__ import annotations
from datetime import date, datetime
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_principal
from app.db.models.accounting import GLAccount, GLJournal, GLJournalLine
from app.db.models.fin_close import FinPeriodClose
from services.accounting.posting import create_auto_journal, ensure_default_mfg_accounts

router = APIRouter(prefix="/accounting", tags=["accounting"])

def _period(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"

@router.post("/seed/min-accounts")
def seed_min_accounts(db: Session = Depends(get_db), principal=Depends(get_principal)):
    codes = ensure_default_mfg_accounts(db)
    return {"ok": True, "accounts": codes}

@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db), limit: int = 500):
    ac = db.query(GLAccount).order_by(GLAccount.account_code.asc()).limit(limit).all()
    return [{"id": a.id, "code": a.account_code, "name": a.account_name, "type": a.account_type} for a in ac]

@router.post("/auto-journal")
def auto_journal(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    lines = payload.get("lines") or []
    if not lines:
        raise HTTPException(400, "lines required")
    try:
        jid = create_auto_journal(
            db,
            actor=principal.username,
            description=payload.get("description") or "Auto Journal",
            source_module=payload.get("source_module") or "AUTO",
            source_document_id=payload.get("source_document_id"),
            lines=lines,
            journal_date=date.fromisoformat(payload["journal_date"]) if payload.get("journal_date") else None,
        )
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "journal_id": jid}

@router.post("/periods/{period}/close")
def close_period(period: str, payload: dict | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    # period format YYYY-MM
    if not re.match(r"^\d{4}-\d{2}$", period):
        raise HTTPException(400, "period must be YYYY-MM")
    row = db.query(FinPeriodClose).filter(FinPeriodClose.period == period).first()
    if not row:
        row = FinPeriodClose(period=period, status="CLOSED", closed_by=principal.username, closed_at=datetime.utcnow(), meta={})
        db.add(row)
    else:
        row.status = "CLOSED"
        row.closed_by = principal.username
        row.closed_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "period": period, "status": "CLOSED"}

@router.post("/periods/{period}/open")
def open_period(period: str, db: Session = Depends(get_db), principal=Depends(get_principal)):
    row = db.query(FinPeriodClose).filter(FinPeriodClose.period == period).first()
    if not row:
        row = FinPeriodClose(period=period, status="OPEN", meta={})
        db.add(row)
    else:
        row.status = "OPEN"
    db.commit()
    return {"ok": True, "period": period, "status": "OPEN"}

@router.get("/periods")
def list_periods(db: Session = Depends(get_db), limit: int = 36):
    rows = db.query(FinPeriodClose).order_by(FinPeriodClose.period.desc()).limit(limit).all()
    return [{"period": r.period, "status": r.status, "closed_by": r.closed_by, "closed_at": str(r.closed_at) if r.closed_at else None} for r in rows]

@router.get("/health")
def health():
    return {"ok": True}
