from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal
from app.db.models.security_audit import AuditLog
from app.db.models.crm import CrmAccount, CrmContact, CrmLead, CrmPipeline, CrmStage, CrmOpportunity, CrmTicket, CrmWorkflowRule
from services.crm.service import ensure_default_pipeline, dashboard_pipeline, add_activity, list_activities

router = APIRouter(prefix="/crm", tags=["crm"])

@router.get("/health")
def health():
    return {"ok": True, "service": "crm"}

@router.post("/bootstrap")
def bootstrap(db: Session = Depends(get_db), p=Depends(get_principal)):
    pipe, stages = ensure_default_pipeline(db)
    return {"pipeline": {"id": pipe.id, "name": pipe.name}, "stages": [{"id": s.id, "name": s.name, "order": s.order} for s in stages]}


# Leads
@router.post("/leads")
def create_lead(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    l = CrmLead(status=payload.get("status","NEW"), source=payload.get("source"), score=payload.get("score",0), owner=p.username, data=payload.get("data",{}))
    db.add(l); db.commit(); db.refresh(l)
    db.add(AuditLog(actor=p.username, action="CRM_CREATE_LEAD", entity_type="CrmLead", entity_id=l.id, reason=payload.get("reason"), data=payload))
    db.commit()
    return {"id": l.id}

@router.get("/leads")
def list_leads(db: Session = Depends(get_db), p=Depends(get_principal)):
    rows = db.query(CrmLead).order_by(CrmLead.created_at.desc()).limit(200).all()
    return [{"id": l.id, "status": l.status, "source": l.source, "score": l.score, "owner": l.owner, "data": l.data} for l in rows]

@router.post("/leads/{lead_id}/convert")
def convert_lead(lead_id: str, payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    l = db.query(CrmLead).filter(CrmLead.id == lead_id).first()
    if not l:
        raise HTTPException(404, "Lead not found")
    # Create account + contact + opportunity (optional)
    acct = CrmAccount(name=payload.get("account_name") or l.data.get("company") or "New Account", industry=payload.get("industry"), status="ACTIVE", owner=p.username)
    db.add(acct); db.flush()
    contact = CrmContact(account_id=acct.id, first_name=payload.get("first_name") or l.data.get("first_name") or "New", last_name=payload.get("last_name") or l.data.get("last_name") or "Contact", email=payload.get("email") or l.data.get("email"))
    db.add(contact); db.flush()
    # ensure pipeline
    from services.crm.service import ensure_default_pipeline
    pipe, stages = ensure_default_pipeline(db)
    opp = None
    if payload.get("create_opportunity", True):
        opp = CrmOpportunity(account_id=acct.id, contact_id=contact.id, pipeline_id=pipe.id, stage_id=stages[0].id,
                             name=payload.get("opportunity_name") or f"Deal for {acct.name}",
                             amount=payload.get("amount", 0), probability=payload.get("probability", 50), status="OPEN", owner=p.username)
        db.add(opp); db.flush()
    l.status = "CONVERTED"
    db.add(AuditLog(actor=p.username, action="CRM_CONVERT_LEAD", entity_type="CrmLead", entity_id=l.id, reason=payload.get("reason"), data={"account_id": acct.id, "contact_id": contact.id, "opp_id": (opp.id if opp else None)}))
    db.commit()
    return {"account_id": acct.id, "contact_id": contact.id, "opportunity_id": (opp.id if opp else None)}
# Accounts
@router.post("/accounts")
def create_account(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    a = CrmAccount(name=payload["name"], industry=payload.get("industry"), status=payload.get("status","ACTIVE"), owner=p.username)
    db.add(a); db.commit(); db.refresh(a)
    db.add(AuditLog(actor=p.username, action="CRM_CREATE_ACCOUNT", entity_type="CrmAccount", entity_id=a.id, reason=payload.get("reason"), data=payload))
    db.commit()
    return {"id": a.id, "name": a.name}

@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db), p=Depends(get_principal)):
    rows = db.query(CrmAccount).order_by(CrmAccount.created_at.desc()).limit(200).all()
    return [{"id": a.id, "name": a.name, "industry": a.industry, "status": a.status, "owner": a.owner} for a in rows]

@router.get("/accounts/{account_id}")
def get_account(account_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    a = db.query(CrmAccount).filter(CrmAccount.id == account_id).first()
    if not a:
        raise HTTPException(404, "Account not found")
    return {"id": a.id, "name": a.name, "industry": a.industry, "status": a.status, "owner": a.owner, "parent_account_id": a.parent_account_id}

# Contacts
@router.post("/contacts")
def create_contact(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    c = CrmContact(
        account_id=payload.get("account_id"),
        first_name=payload["first_name"],
        last_name=payload["last_name"],
        title=payload.get("title"),
        email=payload.get("email"),
        phone=payload.get("phone"),
        lifecycle_stage=payload.get("lifecycle_stage","PROSPECT"),
    )
    db.add(c); db.commit(); db.refresh(c)
    db.add(AuditLog(actor=p.username, action="CRM_CREATE_CONTACT", entity_type="CrmContact", entity_id=c.id, reason=payload.get("reason"), data=payload))
    db.commit()
    return {"id": c.id}

@router.get("/contacts")
def list_contacts(db: Session = Depends(get_db), p=Depends(get_principal)):
    rows = db.query(CrmContact).order_by(CrmContact.created_at.desc()).limit(200).all()
    return [{
        "id": c.id,
        "account_id": c.account_id,
        "name": f"{c.first_name} {c.last_name}",
        "email": c.email,
        "phone": c.phone,
        "lifecycle_stage": c.lifecycle_stage,
    } for c in rows]

# Pipeline / opportunities
@router.get("/pipelines")
def list_pipelines(db: Session = Depends(get_db), p=Depends(get_principal)):
    pipes = db.query(CrmPipeline).order_by(CrmPipeline.name.asc()).all()
    return [{"id": x.id, "name": x.name} for x in pipes]

@router.get("/pipelines/{pipeline_id}/stages")
def list_stages(pipeline_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    st = db.query(CrmStage).filter(CrmStage.pipeline_id == pipeline_id).order_by(CrmStage.order.asc()).all()
    return [{"id": s.id, "name": s.name, "order": s.order} for s in st]

@router.post("/opportunities")
def create_opportunity(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    # Ensure pipeline/stage exist
    pipeline_id = payload.get("pipeline_id")
    stage_id = payload.get("stage_id")
    if not pipeline_id or not stage_id:
        pipe, stages = ensure_default_pipeline(db)
        pipeline_id = pipe.id
        stage_id = stages[0].id  # Lead
    o = CrmOpportunity(
        account_id=payload.get("account_id"),
        contact_id=payload.get("contact_id"),
        pipeline_id=pipeline_id,
        stage_id=stage_id,
        name=payload["name"],
        amount=payload.get("amount", 0),
        close_date=payload.get("close_date"),
        probability=payload.get("probability", 50),
        status=payload.get("status","OPEN"),
        owner=p.username
    )
    db.add(o); db.commit(); db.refresh(o)
    db.add(AuditLog(actor=p.username, action="CRM_CREATE_OPPORTUNITY", entity_type="CrmOpportunity", entity_id=o.id, reason=payload.get("reason"), data=payload))
    db.commit()
    return {"id": o.id}

@router.get("/pipelines/{pipeline_id}/board")
def pipeline_board(pipeline_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    stages, by_stage = dashboard_pipeline(db, pipeline_id)
    return {
        "stages": [{"id": s.id, "name": s.name, "order": s.order} for s in stages],
        "opps": {
            sid: [{"id": o.id, "name": o.name, "amount": float(o.amount), "account_id": o.account_id, "probability": o.probability} for o in ops]
            for sid, ops in by_stage.items()
        }
    }

@router.post("/opportunities/{opp_id}/move")
def move_opp(opp_id: str, payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    o = db.query(CrmOpportunity).filter(CrmOpportunity.id == opp_id).first()
    if not o:
        raise HTTPException(404, "Opportunity not found")
    o.stage_id = payload["stage_id"]
    db.add(AuditLog(actor=p.username, action="CRM_MOVE_OPPORTUNITY", entity_type="CrmOpportunity", entity_id=o.id, reason=payload.get("reason"), data=payload))
    db.commit()
    return {"ok": True}


# Workflow Rules (starter)
@router.post("/workflow-rules")
def create_rule(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    r = CrmWorkflowRule(
        name=payload["name"],
        is_enabled=1 if payload.get("is_enabled", True) else 0,
        trigger=payload["trigger"],
        condition=payload.get("condition", {}),
        action=payload.get("action", {}),
    )
    db.add(r); db.commit(); db.refresh(r)
    db.add(AuditLog(actor=p.username, action="CRM_CREATE_WORKFLOW_RULE", entity_type="CrmWorkflowRule", entity_id=r.id, reason=payload.get("reason"), data=payload))
    db.commit()
    return {"id": r.id}

@router.get("/workflow-rules")
def list_rules(db: Session = Depends(get_db), p=Depends(get_principal)):
    rows = db.query(CrmWorkflowRule).order_by(CrmWorkflowRule.created_at.desc()).limit(200).all()
    return [{"id": r.id, "name": r.name, "trigger": r.trigger, "is_enabled": bool(r.is_enabled), "condition": r.condition, "action": r.action} for r in rows]
# Tickets
@router.post("/tickets")
def create_ticket(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    t = CrmTicket(
        account_id=payload.get("account_id"),
        contact_id=payload.get("contact_id"),
        subject=payload["subject"],
        description=payload.get("description"),
        status=payload.get("status","OPEN"),
        severity=payload.get("severity","MED"),
        owner=p.username,
        sla_due_at=payload.get("sla_due_at"),
    )
    db.add(t); db.commit(); db.refresh(t)
    db.add(AuditLog(actor=p.username, action="CRM_CREATE_TICKET", entity_type="CrmTicket", entity_id=t.id, reason=payload.get("reason"), data=payload))
    db.commit()
    return {"id": t.id}

@router.get("/tickets")
def list_tickets(db: Session = Depends(get_db), p=Depends(get_principal)):
    rows = db.query(CrmTicket).order_by(CrmTicket.created_at.desc()).limit(200).all()
    return [{"id": t.id, "subject": t.subject, "status": t.status, "severity": t.severity, "account_id": t.account_id} for t in rows]

@router.post("/tickets/{ticket_id}/status")
def set_ticket_status(ticket_id: str, payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    t = db.query(CrmTicket).filter(CrmTicket.id == ticket_id).first()
    if not t:
        raise HTTPException(404, "Ticket not found")
    t.status = payload["status"]
    db.add(AuditLog(actor=p.username, action="CRM_UPDATE_TICKET", entity_type="CrmTicket", entity_id=t.id, reason=payload.get("reason"), data=payload))
    db.commit()
    return {"ok": True}

# Activity timeline
@router.post("/activities")
def create_activity(payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    act = add_activity(
        db,
        entity_type=payload["entity_type"],
        entity_id=payload["entity_id"],
        type=payload.get("type","NOTE"),
        subject=payload.get("subject"),
        body=payload.get("body"),
        actor=p.username
    )
    db.add(AuditLog(actor=p.username, action="CRM_ADD_ACTIVITY", entity_type="CrmActivity", entity_id=act.id, reason=payload.get("reason"), data=payload))
    db.commit()
    return {"id": act.id}

@router.get("/activities")
def get_activities(entity_type: str, entity_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    acts = list_activities(db, entity_type, entity_id)
    return [{
        "id": a.id,
        "occurred_at": a.occurred_at.isoformat(),
        "type": a.type,
        "subject": a.subject,
        "body": a.body,
        "actor": a.actor,
        "meta": a.meta,
    } for a in acts]
