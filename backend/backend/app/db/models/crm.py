from __future__ import annotations
from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt

class CrmAccount(Base, HasId, HasCreatedAt):
    __tablename__ = "crm_account"
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)  # ACTIVE|INACTIVE
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_account_id: Mapped[str | None] = mapped_column(ForeignKey("crm_account.id"), nullable=True, index=True)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    parent: Mapped["CrmAccount"] = relationship(remote_side="CrmAccount.id", uselist=False)

class CrmContact(Base, HasId, HasCreatedAt):
    __tablename__ = "crm_contact"
    account_id: Mapped[str | None] = mapped_column(ForeignKey("crm_account.id"), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lifecycle_stage: Mapped[str] = mapped_column(String(32), default="PROSPECT", nullable=False)  # PROSPECT|CUSTOMER|CHURNED

    account: Mapped[CrmAccount | None] = relationship()

class CrmLead(Base, HasId, HasCreatedAt):
    __tablename__ = "crm_lead"
    status: Mapped[str] = mapped_column(String(24), default="NEW", nullable=False)  # NEW|QUALIFIED|DISQUALIFIED|CONVERTED
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # captured form fields (flexible)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class CrmPipeline(Base, HasId, HasCreatedAt):
    __tablename__ = "crm_pipeline"
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

class CrmStage(Base, HasId, HasCreatedAt):
    __tablename__ = "crm_stage"
    pipeline_id: Mapped[str] = mapped_column(ForeignKey("crm_pipeline.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    pipeline: Mapped[CrmPipeline] = relationship()

class CrmOpportunity(Base, HasId, HasCreatedAt):
    __tablename__ = "crm_opportunity"
    account_id: Mapped[str | None] = mapped_column(ForeignKey("crm_account.id"), nullable=True, index=True)
    contact_id: Mapped[str | None] = mapped_column(ForeignKey("crm_contact.id"), nullable=True, index=True)
    pipeline_id: Mapped[str] = mapped_column(ForeignKey("crm_pipeline.id"), nullable=False, index=True)
    stage_id: Mapped[str] = mapped_column(ForeignKey("crm_stage.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    probability: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False)  # OPEN|WON|LOST
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    account: Mapped[CrmAccount | None] = relationship()
    contact: Mapped[CrmContact | None] = relationship()
    pipeline: Mapped[CrmPipeline] = relationship()
    stage: Mapped[CrmStage] = relationship()

class CrmActivity(Base, HasId, HasCreatedAt):
    __tablename__ = "crm_activity"
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    type: Mapped[str] = mapped_column(String(24), nullable=False)  # NOTE|CALL|EMAIL|MEETING|SYSTEM
    subject: Mapped[str | None] = mapped_column(String(256), nullable=True)
    body: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # polymorphic "related-to"
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)  # ACCOUNT|CONTACT|OPPORTUNITY|TICKET
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class CrmTicket(Base, HasId, HasCreatedAt):
    __tablename__ = "crm_ticket"
    account_id: Mapped[str | None] = mapped_column(ForeignKey("crm_account.id"), nullable=True, index=True)
    contact_id: Mapped[str | None] = mapped_column(ForeignKey("crm_contact.id"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False)  # OPEN|IN_PROGRESS|RESOLVED|CLOSED
    severity: Mapped[str] = mapped_column(String(16), default="MED", nullable=False)  # LOW|MED|HIGH|CRIT
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped[CrmAccount | None] = relationship()
    contact: Mapped[CrmContact | None] = relationship()

class CrmWorkflowRule(Base, HasId, HasCreatedAt):
    __tablename__ = "crm_workflow_rule"
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)  # 1/0
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. EmailOpened
    condition: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    action: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
