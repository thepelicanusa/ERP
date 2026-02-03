"""
MODULE: EMAIL ENGINE (Inbound/Outbound + Tracking)
Option A: Per-user SMTP/IMAP credentials.

This is starter scaffolding intended to be safe-by-default:
- credentials are stored encrypted when EMAIL_CRED_MASTER_KEY is set
- inbound messages that cannot be confidently routed go to triage
"""

from __future__ import annotations

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Integer, JSON, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional


class EmailAccount(Base, HasId, HasCreatedAt):
    # Prefixed table names to avoid conflicts with other modules
    __tablename__ = "ee_email_account"

    # ERP user identifier (ties mailbox to an ERP user)
    user_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Identity
    email_address: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)

    # SMTP
    smtp_host: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    smtp_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    smtp_username: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    smtp_password_enc: Mapped[str] = mapped_column(Text, nullable=False, default="")  # encrypted

    # IMAP
    imap_host: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, default=993)
    imap_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    imap_username: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    imap_password_enc: Mapped[str] = mapped_column(Text, nullable=False, default="")  # encrypted

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class EmailMessage(Base, HasId, HasCreatedAt):
    __tablename__ = "ee_email_message"

    # INBOUND | OUTBOUND
    direction: Mapped[str] = mapped_column(String(16), index=True, nullable=False)

    # DRAFT | QUEUED | SENT | FAILED | RECEIVED
    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False, default="DRAFT")

    # mailbox owner (user_name) responsible for this message
    owner_user_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False, default="")

    from_email: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    to_emails: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cc_emails: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    bcc_emails: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    subject: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # RFC headers for threading
    smtp_message_id: Mapped[str | None] = mapped_column(String(512), index=True, nullable=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(512), index=True, nullable=True)
    references: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Correlation for routing
    correlation_token: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    thread_key: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)

    # Link to ERP record
    erp_model: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    erp_record_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    attachments = relationship("EmailAttachment", back_populates="message")
    events = relationship("EmailEvent", back_populates="message")


class EmailAttachment(Base, HasId, HasCreatedAt):
    __tablename__ = "ee_email_attachment"

    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("ee_email_message.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False, default="")
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False, default="")

    message = relationship("EmailMessage", back_populates="attachments")


class EmailEvent(Base, HasId, HasCreatedAt):
    __tablename__ = "ee_email_event"

    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("ee_email_message.id"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # OPEN|CLICK|REPLY|BOUNCE|DELIVERED
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    message = relationship("EmailMessage", back_populates="events")


class EmailTriage(Base, HasId, HasCreatedAt):
    __tablename__ = "ee_email_triage"

    inbound_message_id: Mapped[str] = mapped_column(String(36), ForeignKey("ee_email_message.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False, default="OPEN")  # OPEN|RESOLVED
    reason: Mapped[str] = mapped_column(String(256), nullable=False, default="UNROUTED")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-100
    suggested_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    suggested_record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_ee_email_triage_status_created", "status", "created_at"),
    )
