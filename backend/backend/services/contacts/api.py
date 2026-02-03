from __future__ import annotations

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_principal
from app.db.session import get_db
from app.db.models.contacts import (
    LegalEntity, Party, PartyProfile, PartyProfileRole, PartyRole, PartyType,
    PartyContactMethod, ContactMethodType
)

router = APIRouter(prefix="/contacts", tags=["contacts"])

def _tenant_id() -> str:
    return "default"

@router.post("/legal-entities")
def create_legal_entity(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    code = (payload.get("code") or "MAIN").upper()
    name = payload.get("name") or code
    le = db.query(LegalEntity).filter(LegalEntity.tenant_id==_tenant_id(), LegalEntity.code==code).first()
    if le:
        return {"id": le.id, "code": le.code, "name": le.name}
    le = LegalEntity(id=str(uuid.uuid4()), tenant_id=_tenant_id(), code=code, name=name)
    db.add(le); db.commit()
    return {"id": le.id, "code": le.code, "name": le.name}

@router.get("/legal-entities")
def list_legal_entities(db: Session = Depends(get_db), principal=Depends(get_principal)):
    rows = db.query(LegalEntity).filter(LegalEntity.tenant_id==_tenant_id()).order_by(LegalEntity.code.asc()).all()
    return [{"id": r.id, "code": r.code, "name": r.name} for r in rows]

@router.post("/parties")
def create_party(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    party_type = payload.get("party_type")
    if party_type not in ("PERSON","ORG"):
        raise HTTPException(400, "party_type must be PERSON or ORG")
    p = Party(
        id=str(uuid.uuid4()),
        tenant_id=_tenant_id(),
        party_type=PartyType(party_type),
        display_name=payload.get("display_name") or "",
        legal_name=payload.get("legal_name"),
        tax_id=payload.get("tax_id"),
        website=payload.get("website"),
        is_active=True,
    )
    if not p.display_name:
        raise HTTPException(400, "display_name is required")
    db.add(p)
    db.flush()

    for cm in payload.get("contact_methods") or []:
        cm_type = cm.get("type")
        if cm_type not in ("EMAIL","PHONE","OTHER"):
            continue
        db.add(PartyContactMethod(
            party_id=p.id,
            type=ContactMethodType(cm_type),
            label=cm.get("label"),
            value=cm.get("value") or "",
            is_primary=bool(cm.get("is_primary", False)),
            is_verified=bool(cm.get("is_verified", False)),
        ))
    db.commit()
    return {"id": p.id, "party_type": p.party_type.value, "display_name": p.display_name}

@router.get("/parties")
def search_parties(q: str | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    qry = db.query(Party).filter(Party.tenant_id==_tenant_id())
    if q:
        like = f"%{q}%"
        qry = qry.filter(Party.display_name.ilike(like))
    rows = qry.order_by(Party.display_name.asc()).limit(50).all()
    return [{"id": r.id, "party_type": r.party_type.value, "display_name": r.display_name} for r in rows]

@router.post("/parties/{party_id}/profiles")
def create_profile(party_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    le_id = payload.get("legal_entity_id")
    if not le_id:
        # auto-pick MAIN if exists
        le = db.query(LegalEntity).filter(LegalEntity.tenant_id==_tenant_id(), LegalEntity.code=="MAIN").first()
        if not le:
            le = LegalEntity(id=str(uuid.uuid4()), tenant_id=_tenant_id(), code="MAIN", name="Main")
            db.add(le); db.flush()
        le_id = le.id

    party = db.query(Party).filter(Party.tenant_id==_tenant_id(), Party.id==party_id).first()
    if not party:
        raise HTTPException(404, "party not found")

    existing = db.query(PartyProfile).filter(PartyProfile.tenant_id==_tenant_id(), PartyProfile.legal_entity_id==le_id, PartyProfile.party_id==party_id).first()
    if existing:
        return {"id": existing.id, "party_id": existing.party_id, "legal_entity_id": existing.legal_entity_id}

    prof = PartyProfile(id=str(uuid.uuid4()), tenant_id=_tenant_id(), legal_entity_id=le_id, party_id=party_id)
    db.add(prof); db.commit()
    return {"id": prof.id, "party_id": prof.party_id, "legal_entity_id": prof.legal_entity_id}

@router.put("/profiles/{profile_id}/roles")
def set_roles(profile_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    roles = payload.get("roles") or []
    roles = [r for r in roles if r in ("CUSTOMER","VENDOR")]
    prof = db.query(PartyProfile).filter(PartyProfile.tenant_id==_tenant_id(), PartyProfile.id==profile_id).first()
    if not prof:
        raise HTTPException(404, "profile not found")

    existing = {r.role.value: r for r in db.query(PartyProfileRole).filter(PartyProfileRole.party_profile_id==profile_id).all()}
    # enable requested
    for r in roles:
        row = existing.get(r)
        if row:
            row.is_active = True
        else:
            db.add(PartyProfileRole(party_profile_id=profile_id, role=PartyRole(r), is_active=True))
    # disable others
    for key, row in existing.items():
        if key not in roles:
            row.is_active = False
    db.commit()
    return {"ok": True, "profile_id": profile_id, "roles": roles}

@router.get("/parties/{party_id}/smart-buttons")
def smart_buttons(party_id: str, legal_entity_id: str, db: Session = Depends(get_db), principal=Depends(get_principal)):
    # This is a lightweight placeholder that other modules can extend via a provider registry later.
    prof = db.query(PartyProfile).filter(
        PartyProfile.tenant_id==_tenant_id(),
        PartyProfile.party_id==party_id,
        PartyProfile.legal_entity_id==legal_entity_id,
    ).first()
    if not prof:
        raise HTTPException(404, "party profile not found for legal_entity_id")

    roles = [r.role.value for r in db.query(PartyProfileRole).filter(PartyProfileRole.party_profile_id==prof.id, PartyProfileRole.is_active==True).all()]

    buttons = []
    # Support tickets count
    try:
        from app.db.models.support import SupportTicket
        tcount = db.query(SupportTicket).filter(SupportTicket.tenant_id==_tenant_id(), SupportTicket.party_profile_id==prof.id).count()
        buttons.append({"key": "support_tickets", "label": "Tickets", "count": tcount, "route": f"/support/tickets?party_profile_id={prof.id}"})
    except Exception:
        pass

    return {"party_id": party_id, "legal_entity_id": legal_entity_id, "party_profile_id": prof.id, "roles": roles, "buttons": buttons}
