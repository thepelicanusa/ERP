from __future__ import annotations

import enum
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from app.db.base import Base

class TicketPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class SupportTicket(Base):
    __tablename__ = "support_ticket"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    legal_entity_id = Column(String(36), nullable=True, index=True)
    party_profile_id = Column(String(36), ForeignKey("party_profile.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False, index=True)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False, index=True)

    assigned_user_id = Column(String(64), nullable=True, index=True)
    sla_due_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_support_ticket_tenant_status_priority", "tenant_id", "status", "priority"),
    )

class SupportTicketComment(Base):
    __tablename__ = "support_ticket_comment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(36), ForeignKey("support_ticket.id"), nullable=False, index=True)
    author_user_id = Column(String(64), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
