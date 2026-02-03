from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_principal
from app.core.tenant import get_tenant_id
from app.db.models.employee import Employee, EmployeeAsset, EmployeeDocument, EmployeeDocumentTemplate, EmployeeOffboardingItem
from app.db.models.security_audit import AuditLog
from app.db.session import get_db


router = APIRouter(prefix="/employee", tags=["employee"])


def _audit(db: Session, tenant_id: str, actor: str, action: str, entity_type: str, entity_id: str | None, payload: dict):
    try:
        db.add(AuditLog(
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        ))
        db.flush()
    except Exception:
        # Never block core flow on audit failures
        pass


def _roles(principal) -> set[str]:
    return set(getattr(principal, "roles", None) or [])


def _is_admin(principal) -> bool:
    return "ADMIN" in _roles(principal)


def _is_hr(principal) -> bool:
    # In this repo, auth is stubbed; treat ADMIN as HR-equivalent.
    return "HR" in _roles(principal) or _is_admin(principal)


def _is_payroll(principal) -> bool:
    return "PAYROLL" in _roles(principal) or _is_admin(principal)


def _mask_employee_row(row: Employee, principal) -> dict:
    data = {
        "id": row.id,
        "employee_code": row.employee_code,
        "legal_first_name": row.legal_first_name,
        "legal_last_name": row.legal_last_name,
        "legal_middle_name": row.legal_middle_name,
        "preferred_name": row.preferred_name,
        "pronouns": row.pronouns,
        "photo_url": row.photo_url,
        "work_email": row.work_email,
        "work_phone": row.work_phone,
        "emergency_contact_name": row.emergency_contact_name,
        "emergency_contact_phone": row.emergency_contact_phone,
        "emergency_contact_relationship": row.emergency_contact_relationship,
        "visa_status": row.visa_status,
        "visa_expiry_at": row.visa_expiry_at.isoformat() if row.visa_expiry_at else None,
        "start_at": row.start_at.isoformat() if row.start_at else None,
        "probation_end_at": row.probation_end_at.isoformat() if row.probation_end_at else None,
        "end_at": row.end_at.isoformat() if row.end_at else None,
        "status": row.status,
        "contract_type": row.contract_type,
        "fte_pct": str(row.fte_pct) if row.fte_pct is not None else None,
        "job_title": row.job_title,
        "job_grade": row.job_grade,
        "cost_center": row.cost_center,
        "department": row.department,
        "location": row.location,
        "work_site": row.work_site,
        "manager_employee_id": row.manager_employee_id,
        "dotted_manager_employee_id": row.dotted_manager_employee_id,
        "user_id": row.user_id,
        "currency": row.currency,
        "meta": row.meta or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }

    # Restricted fields only for HR/Payroll/Admin
    if _is_hr(principal) or _is_payroll(principal):
        data.update(
            {
                "national_id": row.national_id,
                "tax_id": row.tax_id,
                "salary_annual": str(row.salary_annual) if row.salary_annual is not None else None,
                "hourly_rate": str(row.hourly_rate) if row.hourly_rate is not None else None,
            }
        )
    else:
        data.update({"national_id": None, "tax_id": None, "salary_annual": None, "hourly_rate": None})

    return data


def _parse_dt(v) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(v)
    except Exception:
        return None


def _get_manager_employee(db: Session, tenant_id: str, principal) -> Employee | None:
    # Map principal.username -> Employee.user_id
    username = getattr(principal, "username", None)
    if not username:
        return None
    return (
        db.query(Employee)
        .filter(Employee.tenant_id == tenant_id, Employee.user_id == username)
        .order_by(Employee.created_at.desc())
        .first()
    )


def _can_read_employee(db: Session, tenant_id: str, principal, emp: Employee) -> bool:
    if _is_hr(principal) or _is_payroll(principal) or _is_admin(principal):
        return True
    # self
    if emp.user_id and emp.user_id == getattr(principal, "username", None):
        return True
    # manager (direct or dotted)
    mgr = _get_manager_employee(db, tenant_id, principal)
    if mgr and (emp.manager_employee_id == mgr.id or emp.dotted_manager_employee_id == mgr.id):
        return True
    return False


def _require_hr_or_admin(principal) -> None:
    if not _is_hr(principal):
        raise HTTPException(403, "HR/Admin role required")


@router.get("/employees")
def list_employees(
    db: Session = Depends(get_db),
    principal=Depends(get_principal),
    limit: int = 200,
):
    tenant_id = get_tenant_id()

    qs = db.query(Employee).filter(Employee.tenant_id == tenant_id)
    if not (_is_hr(principal) or _is_payroll(principal) or _is_admin(principal)):
        # Non-privileged users only see self (if linked)
        qs = qs.filter(Employee.user_id == getattr(principal, "username", ""))

    rows = qs.order_by(Employee.created_at.desc()).limit(limit).all()
    return [_mask_employee_row(r, principal) for r in rows]


@router.post("/employees")
def create_employee(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()

    code = payload.get("employee_code") or payload.get("employee_id")
    if not code:
        raise HTTPException(400, "employee_code is required")

    existing = (
        db.query(Employee)
        .filter(Employee.tenant_id == tenant_id, Employee.employee_code == code)
        .first()
    )
    if existing:
        raise HTTPException(409, "employee_code already exists")

    e = Employee(
        tenant_id=tenant_id,
        employee_code=code,
        legal_first_name=payload.get("legal_first_name") or payload.get("first_name") or "",
        legal_last_name=payload.get("legal_last_name") or payload.get("last_name") or "",
        legal_middle_name=payload.get("legal_middle_name"),
        preferred_name=payload.get("preferred_name"),
        pronouns=payload.get("pronouns"),
        photo_url=payload.get("photo_url"),
        work_email=payload.get("work_email"),
        work_phone=payload.get("work_phone"),
        emergency_contact_name=payload.get("emergency_contact_name"),
        emergency_contact_phone=payload.get("emergency_contact_phone"),
        emergency_contact_relationship=payload.get("emergency_contact_relationship"),
        national_id=payload.get("national_id"),
        tax_id=payload.get("tax_id"),
        visa_status=payload.get("visa_status"),
        visa_expiry_at=_parse_dt(payload.get("visa_expiry_at")),
        start_at=_parse_dt(payload.get("start_at")),
        probation_end_at=_parse_dt(payload.get("probation_end_at")),
        end_at=_parse_dt(payload.get("end_at")),
        status=payload.get("status") or "ACTIVE",
        contract_type=payload.get("contract_type") or "FT",
        fte_pct=Decimal(str(payload.get("fte_pct"))) if payload.get("fte_pct") is not None else Decimal("100.00"),
        job_title=payload.get("job_title"),
        job_grade=payload.get("job_grade"),
        cost_center=payload.get("cost_center"),
        department=payload.get("department"),
        location=payload.get("location"),
        work_site=payload.get("work_site"),
        manager_employee_id=payload.get("manager_employee_id"),
        dotted_manager_employee_id=payload.get("dotted_manager_employee_id"),
        user_id=payload.get("user_id"),
        currency=payload.get("currency") or "USD",
        salary_annual=Decimal(str(payload.get("salary_annual"))) if payload.get("salary_annual") is not None else None,
        hourly_rate=Decimal(str(payload.get("hourly_rate"))) if payload.get("hourly_rate") is not None else None,
        meta=payload.get("meta") or {},
    )
    if not e.legal_first_name or not e.legal_last_name:
        raise HTTPException(400, "legal_first_name and legal_last_name are required")

    db.add(e)
    db.commit()
    db.refresh(e)
    return {"id": e.id, "employee_code": e.employee_code}


@router.get("/employees/{employee_id}")
def get_employee(employee_id: str, db: Session = Depends(get_db), principal=Depends(get_principal)):
    tenant_id = get_tenant_id()
    e = db.query(Employee).filter(Employee.tenant_id == tenant_id, Employee.id == employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")
    if not _can_read_employee(db, tenant_id, principal, e):
        raise HTTPException(403, "Not allowed")
    return _mask_employee_row(e, principal)


@router.patch("/employees/{employee_id}")
def update_employee(employee_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    e = db.query(Employee).filter(Employee.tenant_id == tenant_id, Employee.id == employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")
    _s_before = {k: getattr(e, k) for k in ['national_id','tax_id','salary_annual','hourly_rate']}

    # Allow patching a curated set of fields.
    for k in [
        "legal_first_name",
        "legal_last_name",
        "legal_middle_name",
        "preferred_name",
        "pronouns",
        "photo_url",
        "work_email",
        "work_phone",
        "emergency_contact_name",
        "emergency_contact_phone",
        "emergency_contact_relationship",
        "national_id",
        "tax_id",
        "visa_status",
        "status",
        "contract_type",
        "job_title",
        "job_grade",
        "cost_center",
        "department",
        "location",
        "work_site",
        "manager_employee_id",
        "dotted_manager_employee_id",
        "user_id",
        "currency",
        "meta",
    ]:
        if k in payload:
            setattr(e, k, payload.get(k))

    if "fte_pct" in payload and payload.get("fte_pct") is not None:
        e.fte_pct = Decimal(str(payload.get("fte_pct")))
    if "salary_annual" in payload:
        v = payload.get("salary_annual")
        e.salary_annual = Decimal(str(v)) if v is not None else None
    if "hourly_rate" in payload:
        v = payload.get("hourly_rate")
        e.hourly_rate = Decimal(str(v)) if v is not None else None
    if "start_at" in payload:
        e.start_at = _parse_dt(payload.get("start_at"))
    if "probation_end_at" in payload:
        e.probation_end_at = _parse_dt(payload.get("probation_end_at"))
    if "end_at" in payload:
        e.end_at = _parse_dt(payload.get("end_at"))
    if "visa_expiry_at" in payload:
        e.visa_expiry_at = _parse_dt(payload.get("visa_expiry_at"))

        _s_after = {k: getattr(e, k) for k in ['national_id','tax_id','salary_annual','hourly_rate']}
    _diff = {k: {'before': str(_s_before.get(k)), 'after': str(_s_after.get(k))} for k in _s_after if _s_before.get(k)!=_s_after.get(k)}
    if _diff:
        _audit(db, tenant_id, getattr(principal,'username','unknown'), 'HR_EMPLOYEE_SENSITIVE_UPDATE', 'hr_employee', e.id, _diff)
    db.commit()
    db.refresh(e)
    return _mask_employee_row(e, principal)


@router.post("/employees/{employee_id}/terminate")
def terminate_employee(employee_id: str, payload: dict | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    actor = getattr(principal, "username", "unknown")
    e = db.query(Employee).filter(Employee.tenant_id == tenant_id, Employee.id == employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")

    e.status = "TERMINATED"
    e.end_at = _parse_dt((payload or {}).get("end_at")) or datetime.utcnow()

    # Create / refresh offboarding checklist items
    defaults = [
        ("TASK", "Disable accounts / revoke access"),
        ("TASK", "Collect building badge"),
        ("TASK", "Final pay / payroll closeout"),
        ("TASK", "Exit interview (optional)"),
    ]
    for itype, title in defaults:
        existing = (
            db.query(EmployeeOffboardingItem)
            .filter(
                EmployeeOffboardingItem.tenant_id == tenant_id,
                EmployeeOffboardingItem.employee_id == e.id,
                EmployeeOffboardingItem.title == title,
            )
            .first()
        )
        if not existing:
            db.add(EmployeeOffboardingItem(tenant_id=tenant_id, employee_id=e.id, item_type=itype, title=title))

    open_assets = (
        db.query(EmployeeAsset)
        .filter(EmployeeAsset.tenant_id == tenant_id, EmployeeAsset.employee_id == e.id, EmployeeAsset.returned_at.is_(None))
        .all()
    )
    for a in open_assets:
        title = f"Return {a.asset_type}" + (f" ({a.asset_tag})" if a.asset_tag else "")
        existing = (
            db.query(EmployeeOffboardingItem)
            .filter(
                EmployeeOffboardingItem.tenant_id == tenant_id,
                EmployeeOffboardingItem.employee_id == e.id,
                EmployeeOffboardingItem.related_asset_id == a.id,
            )
            .first()
        )
        if not existing:
            db.add(
                EmployeeOffboardingItem(
                    tenant_id=tenant_id,
                    employee_id=e.id,
                    item_type="ASSET",
                    title=title,
                    related_asset_id=a.id,
                )
            )

    _audit(db, tenant_id, actor, "HR_EMPLOYEE_TERMINATE", "hr_employee", e.id, {"end_at": e.end_at.isoformat()})
    db.commit()
    return {"ok": True, "id": e.id, "status": e.status, "end_at": e.end_at.isoformat() if e.end_at else None}


@router.get("/employees/{employee_id}/documents")
def list_documents(employee_id: str, db: Session = Depends(get_db), principal=Depends(get_principal), expiring_days: int = 30):
    tenant_id = get_tenant_id()
    emp = db.query(Employee).filter(Employee.tenant_id == tenant_id, Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    if not _can_read_employee(db, tenant_id, principal, emp):
        raise HTTPException(403, "Not allowed")

    rows = (
        db.query(EmployeeDocument)
        .filter(EmployeeDocument.tenant_id == tenant_id, EmployeeDocument.employee_id == employee_id)
        .order_by(EmployeeDocument.created_at.desc())
        .all()
    )
    return [_doc_to_dict(r, principal, expiring_days) for r in rows]


@router.post("/employees/{employee_id}/documents")
def create_document(employee_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    emp = db.query(Employee).filter(Employee.tenant_id == tenant_id, Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")

    title = payload.get("title")
    if not title:
        raise HTTPException(400, "title is required")

    d = EmployeeDocument(
        tenant_id=tenant_id,
        employee_id=employee_id,
        doc_type=payload.get("doc_type") or "GENERIC",
        title=title,
        version=payload.get("version") or "v1",
        required=bool(payload.get("required", False)),
        attachment_id=payload.get("attachment_id"),
        issued_at=_parse_dt(payload.get("issued_at")),
        expires_at=_parse_dt(payload.get("expires_at")),
        meta=payload.get("meta") or {},
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id}


@router.patch("/documents/{document_id}")
def update_document(document_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    d = db.query(EmployeeDocument).filter(EmployeeDocument.tenant_id == tenant_id, EmployeeDocument.id == document_id).first()
    if not d:
        raise HTTPException(404, "Document not found")

    for k in ["doc_type", "title", "version", "required", "attachment_id", "meta"]:
        if k in payload:
            setattr(d, k, payload.get(k))
    if "issued_at" in payload:
        d.issued_at = _parse_dt(payload.get("issued_at"))
    if "expires_at" in payload:
        d.expires_at = _parse_dt(payload.get("expires_at"))
    db.commit()
    db.refresh(d)
    return _doc_to_dict(d, principal)


@router.get("/documents/expiring")
def list_expiring_documents(db: Session = Depends(get_db), principal=Depends(get_principal), days: int = 30, include_expired: bool = True):
    # HR/Payroll only
    if not (_is_hr(principal) or _is_payroll(principal)):
        raise HTTPException(403, "HR/Payroll role required")
    tenant_id = get_tenant_id()
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days)

    qs = db.query(EmployeeDocument).filter(EmployeeDocument.tenant_id == tenant_id, EmployeeDocument.expires_at.isnot(None))
    if include_expired:
        qs = qs.filter(EmployeeDocument.expires_at <= cutoff)
    else:
        qs = qs.filter(EmployeeDocument.expires_at >= now, EmployeeDocument.expires_at <= cutoff)

    rows = qs.order_by(EmployeeDocument.expires_at.asc()).limit(500).all()
    return [_doc_to_dict(r, principal, days) for r in rows]


def _asset_to_dict(a: EmployeeAsset) -> dict:
    return {
        "id": a.id,
        "employee_id": a.employee_id,
        "asset_type": a.asset_type,
        "asset_tag": a.asset_tag,
        "serial_number": a.serial_number,
        "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        "returned_at": a.returned_at.isoformat() if a.returned_at else None,
        "custody_notes": a.custody_notes,
        "meta": a.meta or {},
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/employees/{employee_id}/assets")
def list_assets(employee_id: str, db: Session = Depends(get_db), principal=Depends(get_principal)):
    tenant_id = get_tenant_id()
    emp = db.query(Employee).filter(Employee.tenant_id == tenant_id, Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    if not _can_read_employee(db, tenant_id, principal, emp):
        raise HTTPException(403, "Not allowed")

    rows = (
        db.query(EmployeeAsset)
        .filter(EmployeeAsset.tenant_id == tenant_id, EmployeeAsset.employee_id == employee_id)
        .order_by(EmployeeAsset.created_at.desc())
        .all()
    )
    return [_asset_to_dict(r) for r in rows]


@router.post("/employees/{employee_id}/assets")
def create_asset(employee_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    emp = db.query(Employee).filter(Employee.tenant_id == tenant_id, Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")

    asset_type = payload.get("asset_type")
    if not asset_type:
        raise HTTPException(400, "asset_type is required")

    a = EmployeeAsset(
        tenant_id=tenant_id,
        employee_id=employee_id,
        asset_type=asset_type,
        asset_tag=payload.get("asset_tag"),
        serial_number=payload.get("serial_number"),
        assigned_at=_parse_dt(payload.get("assigned_at")),
        returned_at=_parse_dt(payload.get("returned_at")),
        custody_notes=payload.get("custody_notes"),
        meta=payload.get("meta") or {},
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id}


@router.patch("/assets/{asset_id}")
def update_asset(asset_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    actor = getattr(principal, "username", "unknown")

    a = db.query(EmployeeAsset).filter(EmployeeAsset.tenant_id == tenant_id, EmployeeAsset.id == asset_id).first()
    if not a:
        raise HTTPException(404, "Asset not found")

    before_returned = a.returned_at

    for k in ["asset_type", "asset_tag", "serial_number", "custody_notes", "meta"]:
        if k in payload:
            setattr(a, k, payload.get(k))
    if "assigned_at" in payload:
        a.assigned_at = _parse_dt(payload.get("assigned_at"))
    if "returned_at" in payload:
        a.returned_at = _parse_dt(payload.get("returned_at"))

    # If asset was returned, auto-complete related offboarding item(s)
    if before_returned is None and a.returned_at is not None:
        items = (
            db.query(EmployeeOffboardingItem)
            .filter(
                EmployeeOffboardingItem.tenant_id == tenant_id,
                EmployeeOffboardingItem.related_asset_id == a.id,
                EmployeeOffboardingItem.status == "OPEN",
            )
            .all()
        )
        for it in items:
            it.status = "DONE"
            it.completed_at = datetime.utcnow()
            it.completed_by = actor

    _audit(db, tenant_id, actor, "HR_ASSET_UPDATE", "hr_employee_asset", a.id, payload or {})
    db.commit()
    db.refresh(a)
    return _asset_to_dict(a)


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/doc_templates")
def list_doc_templates(db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    rows = db.query(EmployeeDocumentTemplate).filter(EmployeeDocumentTemplate.tenant_id == tenant_id).order_by(EmployeeDocumentTemplate.key).all()
    return [{
        "id": r.id,
        "key": r.key,
        "name": r.name,
        "doc_type": r.doc_type,
        "required": r.required,
        "contract_type": r.contract_type,
        "location": r.location,
        "department": r.department,
        "expiry_required": r.expiry_required,
        "default_expiry_days": r.default_expiry_days,
        "meta": r.meta,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]


@router.post("/doc_templates")
def create_doc_template(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    key = (payload or {}).get("key")
    name = (payload or {}).get("name")
    if not key or not name:
        raise HTTPException(400, "key and name are required")
    existing = db.query(EmployeeDocumentTemplate).filter(EmployeeDocumentTemplate.tenant_id == tenant_id, EmployeeDocumentTemplate.key == key).first()
    if existing:
        raise HTTPException(409, "Template key already exists")
    tpl = EmployeeDocumentTemplate(
        tenant_id=tenant_id,
        key=key,
        name=name,
        doc_type=(payload or {}).get("doc_type") or "GENERIC",
        required=bool((payload or {}).get("required", True)),
        contract_type=(payload or {}).get("contract_type"),
        location=(payload or {}).get("location"),
        department=(payload or {}).get("department"),
        expiry_required=bool((payload or {}).get("expiry_required", False)),
        default_expiry_days=(payload or {}).get("default_expiry_days"),
        meta=(payload or {}).get("meta") or {},
    )
    db.add(tpl)
    _audit(db, tenant_id, getattr(principal,'username','unknown'), "HR_DOC_TEMPLATE_CREATE", "hr_document_template", None, {"key": key})
    db.commit()
    db.refresh(tpl)
    return {"id": tpl.id, "key": tpl.key}


@router.patch("/doc_templates/{template_id}")
def update_doc_template(template_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    tpl = db.query(EmployeeDocumentTemplate).filter(EmployeeDocumentTemplate.tenant_id == tenant_id, EmployeeDocumentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")
    for k, v in (payload or {}).items():
        if k in {"key", "id", "tenant_id", "created_at"}:
            continue
        if hasattr(tpl, k):
            setattr(tpl, k, v)
    _audit(db, tenant_id, getattr(principal,'username','unknown'), "HR_DOC_TEMPLATE_UPDATE", "hr_document_template", tpl.id, payload or {})
    db.commit()
    return {"ok": True, "id": tpl.id}


@router.get("/employees/{employee_id}/required_documents")
def employee_required_documents(employee_id: str, db: Session = Depends(get_db), principal=Depends(get_principal)):
    # Read access follows employee read rules
    tenant_id = get_tenant_id()
    e = db.query(Employee).filter(Employee.tenant_id == tenant_id, Employee.id == employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")
    if not _can_read_employee(e, principal, db, tenant_id):
        raise HTTPException(403, "Forbidden")

    templates = db.query(EmployeeDocumentTemplate).filter(EmployeeDocumentTemplate.tenant_id == tenant_id).all()

    def applies(t: EmployeeDocumentTemplate) -> bool:
        if t.contract_type and (e.contract_type or "") != t.contract_type:
            return False
        if t.location and (e.location or "") != t.location:
            return False
        if t.department and (e.department or "") != t.department:
            return False
        return True

    templates = [t for t in templates if applies(t)]
    docs = db.query(EmployeeDocument).filter(EmployeeDocument.tenant_id == tenant_id, EmployeeDocument.employee_id == e.id).all()

    now = datetime.utcnow()
    out = []
    for t in templates:
        candidates = [d for d in docs if (d.doc_type == t.doc_type and (d.meta or {}).get("template_key") == t.key) or d.doc_type == t.key]
        latest = max(candidates, key=lambda d: d.created_at or now, default=None)
        status = "MISSING"
        expires_at = None
        if latest:
            expires_at = latest.expires_at
            if latest.expires_at and latest.expires_at < now:
                status = "EXPIRED"
            elif latest.expires_at and latest.expires_at <= now + timedelta(days=30):
                status = "EXPIRING"
            else:
                status = "OK"
        out.append({
            "template_id": t.id,
            "key": t.key,
            "name": t.name,
            "required": t.required,
            "status": status,
            "document_id": latest.id if latest else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
        })
    return {"employee_id": e.id, "items": out}


@router.get("/employees/{employee_id}/offboarding")
def get_offboarding(employee_id: str, db: Session = Depends(get_db), principal=Depends(get_principal)):
    tenant_id = get_tenant_id()
    e = db.query(Employee).filter(Employee.tenant_id == tenant_id, Employee.id == employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")
    if not _can_read_employee(e, principal, db, tenant_id):
        raise HTTPException(403, "Forbidden")
    items = db.query(EmployeeOffboardingItem).filter(EmployeeOffboardingItem.tenant_id == tenant_id, EmployeeOffboardingItem.employee_id == e.id).order_by(EmployeeOffboardingItem.created_at).all()
    return {"employee_id": e.id, "status": e.status, "items": [{
        "id": it.id,
        "item_type": it.item_type,
        "title": it.title,
        "status": it.status,
        "related_asset_id": it.related_asset_id,
        "completed_at": it.completed_at.isoformat() if it.completed_at else None,
        "completed_by": it.completed_by,
        "waiver_reason": it.waiver_reason,
        "meta": it.meta,
    } for it in items]}


@router.patch("/offboarding/{item_id}")
def update_offboarding_item(item_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_hr_or_admin(principal)
    tenant_id = get_tenant_id()
    actor = getattr(principal, "username", "unknown")
    it = db.query(EmployeeOffboardingItem).filter(EmployeeOffboardingItem.tenant_id == tenant_id, EmployeeOffboardingItem.id == item_id).first()
    if not it:
        raise HTTPException(404, "Item not found")
    status = (payload or {}).get("status")
    if status:
        it.status = status
        if status == "DONE":
            it.completed_at = datetime.utcnow()
            it.completed_by = actor
    if (payload or {}).get("waiver_reason") is not None:
        it.waiver_reason = (payload or {}).get("waiver_reason")
    if (payload or {}).get("meta") is not None:
        it.meta = (payload or {}).get("meta") or {}
    _audit(db, tenant_id, actor, "HR_OFFBOARDING_UPDATE", "hr_employee_offboarding_item", it.id, payload or {})
    db.commit()
    return {"ok": True, "id": it.id, "status": it.status}
