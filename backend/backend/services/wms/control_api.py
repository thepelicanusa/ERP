from __future__ import annotations
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_principal
from app.db.models.security_audit import ApprovalRequest
from services.admin.audit import audit
from services.admin.module_guard import get_tenant_id
from services.admin.module_guard import require_module_enabled

from app.db.models.wms.scan_sessions import ScanSession
from app.db.models.wms.session_handoff import SessionHandoff
from app.db.models.wms.qc_hold import QCHold

router = APIRouter(prefix="/wms/control", tags=["wms_control"], dependencies=[Depends(require_module_enabled("wms"))])

def _require_role(principal, role: str):
    roles = set(principal.roles or [])
    if role not in roles:
        raise HTTPException(403, f"{role} role required")

@router.post("/scan-sessions/{session_id}/set-expected-next-scan")
def set_expected_next_scan(session_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_role(principal, "SUPERVISOR")
    s = db.query(ScanSession).filter(ScanSession.id == session_id).first()
    if not s:
        raise HTTPException(404, "session not found")
    s.expected_next_scan = payload.get("expected_next_scan")
    s.hard_lock = bool(payload.get("hard_lock", True))
    db.commit()
    audit(db, tenant_id=get_tenant_id(), actor=principal.username, action="WMS_SET_EXPECTED_NEXT_SCAN", entity_type="ScanSession", entity_id=session_id, payload=payload)
    return {"ok": True, "session_id": session_id, "expected_next_scan": s.expected_next_scan, "hard_lock": s.hard_lock}

@router.post("/scan-sessions/{session_id}/handoff")
def create_handoff(session_id: str, db: Session = Depends(get_db), principal=Depends(get_principal)):
    # operator can request handoff barcode
    s = db.query(ScanSession).filter(ScanSession.id == session_id).first()
    if not s:
        raise HTTPException(404, "session not found")
    barcode = "HS-" + str(uuid.uuid4())[:10].upper()
    h = SessionHandoff(session_id=session_id, barcode=barcode, issued_by=principal.username)
    db.add(h); db.commit(); db.refresh(h)
    audit(db, tenant_id=get_tenant_id(), actor=principal.username, action="WMS_SESSION_HANDOFF_ISSUE", entity_type="SessionHandoff", entity_id=h.id, payload={"barcode": barcode})
    return {"handoff_barcode": barcode}

@router.post("/scan-sessions/resume")
def resume_by_barcode(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    barcode = payload.get("barcode")
    if not barcode:
        raise HTTPException(400, "barcode required")
    h = db.query(SessionHandoff).filter(SessionHandoff.barcode == barcode).first()
    if not h:
        raise HTTPException(404, "handoff not found")
    if h.used:
        raise HTTPException(409, "handoff already used")
    h.used = True
    h.used_at = datetime.utcnow()
    db.commit()
    audit(db, tenant_id=get_tenant_id(), actor=principal.username, action="WMS_SESSION_HANDOFF_RESUME", entity_type="SessionHandoff", entity_id=h.id, payload={"barcode": barcode, "session_id": h.session_id})
    return {"ok": True, "session_id": h.session_id}

@router.post("/override/wrong-item-location")
def request_wrong_item_location_override(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    # Operator requests supervisor approval with reason
    reason = payload.get("reason")
    if not reason:
        raise HTTPException(400, "reason required")
    ar = ApprovalRequest(
        tenant_id=get_tenant_id(),
        request_type="WMS_OVERRIDE_WRONG_ITEM_LOCATION",
        status="PENDING",
        requested_by=principal.username,
        reason=reason,
        payload=payload,
        is_required=True,
    )
    db.add(ar); db.commit(); db.refresh(ar)
    audit(db, tenant_id=get_tenant_id(), actor=principal.username, action="WMS_OVERRIDE_REQUESTED", entity_type="ApprovalRequest", entity_id=ar.id, payload={"reason": reason})
    return {"ok": True, "approval_request_id": ar.id, "status": ar.status}

@router.post("/qc/hold")
def create_qc_hold(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_role(principal, "QA")
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")
    hold_reason = payload.get("hold_reason")
    if not (entity_type and entity_id and hold_reason):
        raise HTTPException(400, "entity_type, entity_id, hold_reason required")
    h = QCHold(entity_type=entity_type, entity_id=entity_id, status="HOLD", hold_reason=hold_reason, held_by=principal.username, meta=payload.get("meta") or {})
    db.add(h); db.commit(); db.refresh(h)
    audit(db, tenant_id=get_tenant_id(), actor=principal.username, action="QC_HOLD", entity_type=entity_type, entity_id=entity_id, payload={"hold_reason": hold_reason})
    return {"ok": True, "qc_hold_id": h.id}

@router.post("/qc/release")
def release_qc_hold(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_role(principal, "SUPERVISOR")
    hold_id = payload.get("qc_hold_id")
    reason = payload.get("reason") or "Supervisor release"
    h = db.query(QCHold).filter(QCHold.id == hold_id).first()
    if not h:
        raise HTTPException(404, "qc hold not found")
    if h.status != "HOLD":
        raise HTTPException(409, "not in HOLD")
    h.status = "RELEASED"
    h.released_by = principal.username
    h.released_at = datetime.utcnow()
    db.commit()
    audit(db, tenant_id=get_tenant_id(), actor=principal.username, action="QC_RELEASE", entity_type=h.entity_type, entity_id=h.entity_id, payload={"qc_hold_id": hold_id, "reason": reason})
    return {"ok": True, "qc_hold_id": hold_id, "status": h.status}
