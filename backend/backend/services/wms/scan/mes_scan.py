from __future__ import annotations
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from typing import Tuple

from app.db.models.wms.scan_sessions import MesScanSession, MesScanEvent
from app.db.models.mes import ProductionOrder, ProductionMaterial
from app.db.models.inventory_exec import InventoryBalance, Location

from services.erp.mes_service import (
    start_operation, issue_material, receive_finished_goods, record_qc
)

VALID_MODES = {"START_OP","ISSUE","RECEIVE","QC"}
EXPECTED_SEQ = {
    # Special states: DECISION (exception resolution)

    "START_OP": ["MO","OP"],
    "ISSUE": ["MO","OP","ITEM","LOC","QTY"],
    "RECEIVE": ["MO","OP","LOC","QTY"],
    "QC": ["MO","OP","CHECK","RESULT"],
}

def _parse(raw: str) -> Tuple[str, str]:
    v = (raw or "").strip()
    up = v.upper()
    if up.startswith("MO:"):
        return ("MO", v.split(":",1)[1].strip())
    if up.startswith("OP:"):
        return ("OP", v.split(":",1)[1].strip())
    if up.startswith("ITEM:"):
        return ("ITEM", v.split(":",1)[1].strip())
    if up.startswith("LOC:"):
        return ("LOC", v.split(":",1)[1].strip())
    if up.startswith("QTY:"):
        return ("QTY", v.split(":",1)[1].strip())
    if up.startswith("CHECK:"):
        return ("CHECK", v.split(":",1)[1].strip())
    if up.startswith('DECISION:'):
        return ('DECISION', v.split(':',1)[1].strip().upper())
    if up.startswith("PASS") or up.startswith("FAIL") or up.startswith("HOLD"):
        return ("RESULT", up)
    # fallbacks: if expected is QTY and raw is numeric we accept in handler
    return ("RAW", v)

def _available_qty(db: Session, *, item_id: str, location_id: str) -> float:
    b = db.query(InventoryBalance).filter(InventoryBalance.item_id == item_id, InventoryBalance.location_id == location_id).first()
    if not b:
        return 0.0
    return float(getattr(b, "qty", 0) or 0)

def _location_exists(db: Session, location_id: str) -> bool:
    return db.query(Location).filter(Location.id == location_id).first() is not None

def _item_required_for_mo(db: Session, mo_id: str, item_id: str) -> bool:
    return db.query(ProductionMaterial).filter(ProductionMaterial.prod_order_id == mo_id, ProductionMaterial.item_id == item_id).first() is not None

def start_session(db: Session, *, mode: str, operator: str) -> MesScanSession:
    mode = mode.upper().strip()
    if mode not in VALID_MODES:
        raise HTTPException(400, f"mode must be one of {sorted(VALID_MODES)}")
    s = MesScanSession(mode=mode, status="ACTIVE", expected=EXPECTED_SEQ[mode][0], operator=operator, context={}, meta={})
    db.add(s); db.commit(); db.refresh(s)
    return s

def get_session(db: Session, session_id: str) -> MesScanSession:
    s = db.query(MesScanSession).filter(MesScanSession.id == session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    return s

def _log(db: Session, s: MesScanSession, raw: str, parsed: dict, result: str, message: str | None, new_expected: str | None):
    db.add(MesScanEvent(session_id=s.id, raw=raw, parsed=parsed, result=result, message=message, new_expected=new_expected))
    db.commit()

def submit_scan(db: Session, *, session_id: str, raw: str, operator: str) -> dict:
    s = get_session(db, session_id)
    if s.status != "ACTIVE":
        raise HTTPException(409, "Session is not ACTIVE")
    if s.operator != operator:
        raise HTTPException(403, "Session owned by different operator")

    kind, value = _parse(raw)
    expected = s.expected
    parsed = {"kind": kind, "value": value, "expected": expected}

    seq = EXPECTED_SEQ[s.mode]
    if expected not in seq:
        raise HTTPException(500, "Invalid session expected state")
    idx = seq.index(expected)

    def reject(msg: str):
        _log(db, s, raw, parsed, "REJECTED", msg, s.expected)
        raise HTTPException(409, msg)

    # normalize RAW based on expected
    if kind == "RAW":
        if expected == "QTY":
            try:
                float(value)
                kind = "QTY"
            except Exception:
                pass
        if expected == "RESULT":
            up = value.upper()
            if up in ("PASS","FAIL","HOLD"):
                kind = "RESULT"
                value = up

    if expected == 'DECISION':
        if kind not in ('DECISION','RAW'):
            reject('Expected DECISION scan')
        choice = value.upper().strip()
        ctx = dict(s.context or {})
        exc = dict((s.meta or {}).get('exception') or {})
        if choice in ('CANCEL','ABORT'):
            s.status = 'CANCELLED'
            s.expected = 'DONE'
            db.add(s); db.commit();
            _log(db, s, raw, {**parsed, 'choice': choice}, 'OK', 'CANCELLED', 'DONE')
            return {'ok': True, 'session_id': s.id, 'status': s.status}
        if choice in ('SHORT','SHORT_ISSUE'):
            # execute issue at available qty
            item_id = ctx.get('item_id'); loc_id = ctx.get('location_id'); mo_id = ctx.get('mo_id');
            if not (item_id and loc_id and mo_id):
                reject('Missing context for short issue')
            avail = _available_qty(db, item_id=item_id, location_id=loc_id)
            if avail <= 0:
                reject('No stock available for short issue')
            req = float(ctx.get('qty') or 0)
            issue_qty = min(avail, req) if req > 0 else avail
            res = issue_material(db, prod_order_id=mo_id, item_id=item_id, from_location_id=loc_id, qty=float(issue_qty), actor=operator)
            s.status = 'COMPLETED'; s.expected = 'DONE'
            s.meta = dict(s.meta or {})
            s.meta['exception_resolved'] = {'type': 'SHORT_ISSUE', 'requested_qty': req, 'issued_qty': issue_qty, 'available': avail, 'ts': datetime.utcnow().isoformat()}
            db.add(s); db.commit();
            _log(db, s, raw, {**parsed, 'choice': choice}, 'OK', 'EXECUTED_SHORT_ISSUE', 'DONE')
            return {'ok': True, 'session_id': s.id, 'status': s.status, 'executed': 'ISSUE_SHORT', 'result': res}
        reject('Unknown decision. Use DECISION:SHORT_ISSUE or DECISION:CANCEL')

    if kind != expected:
        reject(f"Expected {expected} scan")

    ctx = dict(s.context or {})

    # Apply scan to context
    if expected == "MO":
        # allow MO number or id
        mo = db.query(ProductionOrder).filter((ProductionOrder.id == value) | (ProductionOrder.mo_number == value)).first()
        if not mo:
            reject("MO not found")
        ctx["mo_id"] = mo.id
        ctx["mo_number"] = mo.mo_number
    elif expected == "OP":
        try:
            ctx["op_seq"] = int(value)
        except Exception:
            reject("OP scan must be numeric (use OP:<seq>)")
    elif expected == "ITEM":
        # validate BOM membership when MO known
        if ctx.get('mo_id') and not _item_required_for_mo(db, ctx['mo_id'], value):
            reject('Item not required for MO')
        ctx["item_id"] = value
    elif expected == "LOC":
        if not _location_exists(db, value):
            reject('Location not found')
        ctx["location_id"] = value
    elif expected == "QTY":
        try:
            ctx["qty"] = float(value)
        except Exception:
            reject("QTY must be numeric")
    elif expected == "CHECK":
        ctx["check_code"] = value
    elif expected == "RESULT":
        ctx["qc_result"] = value

    # advance expected or execute
    if idx < len(seq) - 1:
        s.context = ctx
        s.expected = seq[idx+1]
        db.add(s); db.commit()
        _log(db, s, raw, parsed, "OK", None, s.expected)
        return {"ok": True, "session_id": s.id, "mode": s.mode, "expected": s.expected, "context": s.context}

    # last step reached -> execute
    s.context = ctx
    db.add(s); db.commit()

    try:
        if s.mode == "START_OP":
            res = start_operation(db, prod_order_id=ctx["mo_id"], seq=int(ctx["op_seq"]), actor=operator)
        elif s.mode == "ISSUE":
            try:
                res = issue_material(db, prod_order_id=ctx["mo_id"], item_id=ctx["item_id"], from_location_id=ctx["location_id"], qty=float(ctx["qty"]), actor=operator)
            except HTTPException as e:
                # Short stock -> exception resolution state
                msg = str(e.detail)
                if 'insufficient' in msg.lower() or 'not enough' in msg.lower() or 'short' in msg.lower():
                    s.meta = dict(s.meta or {})
                    s.meta['exception'] = {'type': 'SHORT_STOCK', 'message': msg, 'options': ['DECISION:SHORT_ISSUE','DECISION:CANCEL'], 'ts': datetime.utcnow().isoformat()}
                    s.expected = 'DECISION'
                    db.add(s); db.commit()
                    _log(db, s, raw, {**parsed, 'exception': s.meta['exception']}, 'REJECTED', msg, 'DECISION')
                    return {'ok': False, 'session_id': s.id, 'expected': 'DECISION', 'exception': s.meta['exception']}
                raise
        elif s.mode == "RECEIVE":
            res = receive_finished_goods(db, prod_order_id=ctx["mo_id"], to_location_id=ctx["location_id"], qty=float(ctx["qty"]), actor=operator)
        elif s.mode == "QC":
            res = record_qc(db, prod_order_id=ctx["mo_id"], seq=int(ctx["op_seq"]), check_code=ctx["check_code"], result=ctx["qc_result"], measured={}, meta={"scan_session": s.id})
        else:
            raise HTTPException(400, "Unsupported mode")
    except HTTPException as e:
        _log(db, s, raw, parsed, "REJECTED", str(e.detail), s.expected)
        raise

    # mark completed
    s.status = "COMPLETED"
    s.expected = "DONE"
    db.add(s); db.commit()
    _log(db, s, raw, parsed, "OK", "EXECUTED", "DONE")
    return {"ok": True, "session_id": s.id, "status": s.status, "executed": s.mode, "result": res}


def list_active_sessions(db: Session, *, operator: str) -> list[dict]:
    rows = db.query(MesScanSession).filter(MesScanSession.operator == operator, MesScanSession.status == "ACTIVE").order_by(MesScanSession.created_at.desc()).limit(50).all()
    return [{"session_id": s.id, "mode": s.mode, "status": s.status, "expected": s.expected, "context": s.context, "meta": s.meta, "created_at": s.created_at.isoformat()} for s in rows]

def cancel_session(db: Session, *, session_id: str, operator: str, note: str | None = None) -> dict:
    s = get_session(db, session_id)
    if s.operator != operator:
        raise HTTPException(403, "Session owned by different operator")
    if s.status != "ACTIVE":
        return {"ok": True, "status": s.status}
    s.status = "CANCELLED"
    s.expected = "DONE"
    s.meta = dict(s.meta or {})
    s.meta["cancel"] = {"note": note, "ts": datetime.utcnow().isoformat()}
    db.add(s); db.commit()
    _log(db, s, "CANCEL", {"note": note}, "OK", "CANCELLED", "DONE")
    return {"ok": True, "status": s.status}
