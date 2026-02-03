from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.db.models.accounting import GLAccount, GLJournal, GLJournalLine
from app.db.models.fin_close import FinPeriodClose

def _period(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"

def ensure_default_mfg_accounts(db: Session) -> dict:
    defaults = [
        ("1200", "Inventory", "ASSET"),
        ("1400", "WIP", "ASSET"),
        ("5100", "Manufacturing Variance", "COGS"),
    ]
    code_to_id = {}
    for code, name, typ in defaults:
        acc = db.query(GLAccount).filter(GLAccount.account_code == code).first()
        if not acc:
            acc = GLAccount(account_code=code, account_name=name, account_type=typ, is_active=True, meta={})
            db.add(acc); db.commit(); db.refresh(acc)
        code_to_id[code] = acc.id
    return code_to_id

def assert_period_open(db: Session, jd: date) -> None:
    period = _period(jd)
    row = db.query(FinPeriodClose).filter(FinPeriodClose.period == period).first()
    if row and row.status == "CLOSED":
        raise ValueError(f"Financial period {period} is CLOSED")

def create_auto_journal(
    db: Session,
    *,
    actor: str,
    description: str,
    source_module: str,
    source_document_id: str | None,
    lines: list[dict],
    journal_date: date | None = None,
) -> str:
    jd = journal_date or date.today()
    assert_period_open(db, jd)
    ensure_default_mfg_accounts(db)

    resolved = []
    for ln in lines:
        code = ln["account_code"]
        acc = db.query(GLAccount).filter(GLAccount.account_code == code).first()
        if not acc:
            raise ValueError(f"Unknown GL account_code: {code}")
        resolved.append((acc.id, ln))

    j = GLJournal(
        journal_number=f"AUTO-{str(uuid.uuid4())[:8].upper()}",
        journal_date=jd,
        posting_date=jd,
        period=_period(jd),
        fiscal_year=jd.year,
        journal_type="AUTO",
        source_module=source_module,
        source_document_id=source_document_id,
        status="POSTED",
        description=description,
        reference=None,
        created_by=actor,
        posted_by=actor,
        posted_at=datetime.utcnow(),
        meta={},
    )
    db.add(j); db.commit(); db.refresh(j)

    total_debit = Decimal("0")
    total_credit = Decimal("0")
    line_no = 1
    for acc_id, ln in resolved:
        debit = Decimal(str(ln.get("debit") or 0))
        credit = Decimal(str(ln.get("credit") or 0))
        total_debit += debit
        total_credit += credit
        db.add(GLJournalLine(
            journal_id=j.id,
            line_number=line_no,
            account_id=acc_id,
            debit_amount=debit,
            credit_amount=credit,
            currency="USD",
            exchange_rate=Decimal("1.0"),
            description=ln.get("description"),
            cost_center_id=None,
            project_id=None,
            department_id=None,
            dimension1=None,
            dimension2=None,
            meta=ln.get("meta") or {},
        ))
        line_no += 1
    if total_debit != total_credit:
        raise ValueError(f"Journal not balanced: debit={total_debit} credit={total_credit}")
    db.commit()
    return j.id
