from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Boolean, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt

class AuditLog(Base, HasId, HasCreatedAt):
    __tablename__ = "sys_audit_log"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Request context for governance-grade audit trails
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_audit_tenant_time", AuditLog.tenant_id, AuditLog.created_at)

class ApprovalRequest(Base, HasId, HasCreatedAt):
    __tablename__ = "sys_approval_request"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    request_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # e.g. WMS_OVERRIDE, QC_RELEASE
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

Index("ix_approval_tenant_status", ApprovalRequest.tenant_id, ApprovalRequest.status)
