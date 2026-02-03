from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.db.models.crm import (
    CrmAccount, CrmContact, CrmPipeline, CrmStage, CrmOpportunity, CrmActivity, CrmTicket
)
from app.core.audit import AuditLog
from app.events.outbox import OutboxEvent

def ensure_default_pipeline(db: Session) -> tuple[CrmPipeline, list[CrmStage]]:
    pipe = db.query(CrmPipeline).filter(CrmPipeline.name == "Default").first()
    if pipe:
        stages = db.query(CrmStage).filter(CrmStage.pipeline_id == pipe.id).order_by(CrmStage.order.asc()).all()
        if stages:
            return pipe, stages
    pipe = CrmPipeline(name="Default")
    db.add(pipe); db.flush()
    stage_names = ["Lead", "Qualified", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
    stages = []
    for i, n in enumerate(stage_names, start=1):
        s = CrmStage(pipeline_id=pipe.id, name=n, order=i)
        db.add(s); stages.append(s)
    db.commit()
    return pipe, stages

def dashboard_pipeline(db: Session, pipeline_id: str):
    stages = db.query(CrmStage).filter(CrmStage.pipeline_id == pipeline_id).order_by(CrmStage.order.asc()).all()
    opps = db.query(CrmOpportunity).filter(CrmOpportunity.pipeline_id == pipeline_id, CrmOpportunity.status == "OPEN").all()
    by_stage: dict[str, list[CrmOpportunity]] = {}
    for o in opps:
        by_stage.setdefault(o.stage_id, []).append(o)
    return stages, by_stage

def add_activity(db: Session, *, entity_type: str, entity_id: str, type: str, subject: str | None, body: str | None, actor: str | None):
    act = CrmActivity(entity_type=entity_type, entity_id=entity_id, type=type, subject=subject, body=body, actor=actor)
    db.add(act)
    db.add(OutboxEvent(topic="CrmActivityAdded", payload={"entity_type": entity_type, "entity_id": entity_id, "type": type, "subject": subject, "actor": actor}))
    db.commit()
    return act

def list_activities(db: Session, entity_type: str, entity_id: str):
    return (db.query(CrmActivity)
            .filter(CrmActivity.entity_type == entity_type, CrmActivity.entity_id == entity_id)
            .order_by(CrmActivity.occurred_at.desc())
            .all())
