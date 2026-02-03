"""
File: apps/api/app/db/models/qms.py
Quality Management System - Inspection, NCR, CAPA, Audit
"""

from __future__ import annotations

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Integer, Numeric, ForeignKey, Enum, JSON, Boolean, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt

# ============= QUALITY CONTROL PLANS =============
class QMSInspectionPlan(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_inspection_plan"
    
    plan_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    plan_name: Mapped[str] = mapped_column(String(256), nullable=False)
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # FK to wms_item
    inspection_type: Mapped[str] = mapped_column(String(32), nullable=False)  # RECEIVING|IN_PROCESS|FINAL|RANDOM
    inspection_stage: Mapped[str] = mapped_column(String(32), nullable=False)  # PRE_RECEIPT|POST_RECEIPT|WIP|FINISHED
    
    # Sampling
    sampling_method: Mapped[str] = mapped_column(String(32), nullable=False)  # FULL|AQL|SKIP_LOT|RANDOM_N
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aql_level: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 1.0|2.5|4.0
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class QMSCheckpoint(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_checkpoint"
    
    inspection_plan_id: Mapped[str] = mapped_column(ForeignKey("qms_inspection_plan.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    checkpoint_name: Mapped[str] = mapped_column(String(256), nullable=False)
    checkpoint_type: Mapped[str] = mapped_column(String(32), nullable=False)  # VISUAL|MEASUREMENT|FUNCTIONAL|DESTRUCTIVE
    
    # Specification
    specification: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurement_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    lower_tolerance: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    upper_tolerance: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    # Acceptance criteria
    accept_on: Mapped[str] = mapped_column(String(16), default="PASS", nullable=False)  # PASS|MEASURE_IN_RANGE|VISUAL_OK
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    plan: Mapped[QMSInspectionPlan] = relationship()

Index("ix_qms_checkpoint_plan_seq", QMSCheckpoint.inspection_plan_id, QMSCheckpoint.sequence)

# ============= INSPECTION EXECUTION =============
class QMSInspection(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_inspection"
    
    inspection_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    inspection_plan_id: Mapped[str] = mapped_column(ForeignKey("qms_inspection_plan.id"), nullable=False, index=True)
    inspection_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    inspector_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # FK to employee
    
    # Source document
    source_document_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # RECEIPT|PRODUCTION_ORDER|SHIPMENT
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Lot/Batch
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lot_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    batch_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Quantities
    lot_size: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    sample_size: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    defect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Result
    status: Mapped[str] = mapped_column(String(16), default="IN_PROGRESS", nullable=False)  # IN_PROGRESS|PASSED|FAILED|CONDITIONAL
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)  # ACCEPT|REJECT|HOLD|CONDITIONAL
    
    # Disposition
    disposition: Mapped[str | None] = mapped_column(String(32), nullable=True)  # ACCEPT|REJECT|REWORK|CONCESSION|SCRAP
    disposition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    plan: Mapped[QMSInspectionPlan] = relationship()

class QMSInspectionResult(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_inspection_result"
    
    inspection_id: Mapped[str] = mapped_column(ForeignKey("qms_inspection.id"), nullable=False, index=True)
    checkpoint_id: Mapped[str] = mapped_column(ForeignKey("qms_checkpoint.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Measurement
    measured_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    measured_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # For visual/text observations
    
    # Result
    result: Mapped[str] = mapped_column(String(16), nullable=False)  # PASS|FAIL|NA|CONDITIONAL
    deviation: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    # Defects
    defect_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    defect_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    inspection: Mapped[QMSInspection] = relationship()
    checkpoint: Mapped[QMSCheckpoint] = relationship()

Index("ix_qms_result_inspection_seq", QMSInspectionResult.inspection_id, QMSInspectionResult.sequence)

# ============= NON-CONFORMANCE REPORTS (NCR) =============
class QMSNCR(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_ncr"
    
    ncr_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    ncr_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reported_by: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Classification
    ncr_type: Mapped[str] = mapped_column(String(32), nullable=False)  # PRODUCT|PROCESS|DOCUMENTATION|SUPPLIER
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # CRITICAL|MAJOR|MINOR
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # INSPECTION|CUSTOMER_COMPLAINT|INTERNAL_AUDIT|PRODUCTION
    
    # Subject
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lot_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    vendor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Description
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity_affected: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    # Root Cause Analysis
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_category: Mapped[str | None] = mapped_column(String(64), nullable=True)  # MATERIAL|EQUIPMENT|METHOD|PERSONNEL|ENVIRONMENT
    
    # Disposition
    immediate_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    disposition: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)  # PENDING|REWORK|SCRAP|USE_AS_IS|RETURN_TO_VENDOR
    disposition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Cost
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Workflow
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)  # OPEN|INVESTIGATING|RESOLVED|CLOSED|CANCELLED
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Links
    inspection_id: Mapped[str | None] = mapped_column(ForeignKey("qms_inspection.id"), nullable=True)
    capa_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # FK to CAPA
    
    attachments: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    inspection: Mapped[QMSInspection | None] = relationship()

# ============= CORRECTIVE & PREVENTIVE ACTION (CAPA) =============
class QMSCAPA(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_capa"
    
    capa_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    capa_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    capa_type: Mapped[str] = mapped_column(String(16), nullable=False)  # CORRECTIVE|PREVENTIVE|BOTH
    
    # Source
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # NCR|AUDIT|COMPLAINT|RISK_ASSESSMENT
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Description
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Actions
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    preventive_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Assignment
    assigned_to: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(64), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Implementation
    implementation_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Verification
    verification_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_result: Mapped[str | None] = mapped_column(String(16), nullable=True)  # EFFECTIVE|NOT_EFFECTIVE|PARTIAL
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)  # OPEN|IN_PROGRESS|IMPLEMENTED|VERIFIED|CLOSED
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Cost
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    attachments: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

# ============= QUALITY AUDITS =============
class QMSAudit(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_audit"
    
    audit_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    audit_type: Mapped[str] = mapped_column(String(32), nullable=False)  # INTERNAL|EXTERNAL|SUPPLIER|CERTIFICATION
    audit_scope: Mapped[str] = mapped_column(String(64), nullable=False)  # PROCESS|PRODUCT|SYSTEM|DOCUMENT
    
    # Schedule
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    
    # Team
    lead_auditor: Mapped[str] = mapped_column(String(64), nullable=False)
    auditors: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # List of auditor IDs
    
    # Subject
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    process_area: Mapped[str | None] = mapped_column(String(128), nullable=True)
    standard: Mapped[str | None] = mapped_column(String(64), nullable=True)  # ISO9001|AS9100|IATF16949
    
    # Findings
    findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    major_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minor_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    observations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="PLANNED", nullable=False)  # PLANNED|IN_PROGRESS|REPORT_DRAFT|COMPLETED|CLOSED
    
    # Report
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    attachments: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class QMSAuditFinding(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_audit_finding"
    
    audit_id: Mapped[str] = mapped_column(ForeignKey("qms_audit.id"), nullable=False, index=True)
    finding_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    finding_type: Mapped[str] = mapped_column(String(16), nullable=False)  # MAJOR|MINOR|OBSERVATION|OFI
    
    clause_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)  # ISO clause number
    area: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Response
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_person: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)  # OPEN|IN_PROGRESS|RESOLVED|VERIFIED|CLOSED
    closure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Link to CAPA
    capa_id: Mapped[str | None] = mapped_column(ForeignKey("qms_capa.id"), nullable=True)
    
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    audit: Mapped[QMSAudit] = relationship()
    capa: Mapped[QMSCAPA | None] = relationship()

# ============= CERTIFICATES & CALIBRATION =============
class QMSCertificate(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_certificate"
    
    certificate_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    certificate_type: Mapped[str] = mapped_column(String(32), nullable=False)  # COC|COA|CALIBRATION|MATERIAL_CERT
    
    # Subject
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lot_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    equipment_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Issuer
    issued_by: Mapped[str] = mapped_column(String(256), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    
    # Content
    test_results: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    specifications_met: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Document
    document_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    document_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)  # ACTIVE|EXPIRED|REVOKED
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

# ============= CUSTOMER COMPLAINTS =============
class QMSComplaint(Base, HasId, HasCreatedAt):
    __tablename__ = "qms_complaint"
    
    complaint_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    complaint_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Customer
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # FK to ar_customer
    customer_contact: Mapped[str | None] = mapped_column(String(256), nullable=True)
    
    # Source
    source_channel: Mapped[str] = mapped_column(String(32), nullable=False)  # EMAIL|PHONE|WEB|IN_PERSON
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Order, Invoice, etc.
    
    # Product
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lot_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    quantity_affected: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    # Complaint
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # QUALITY|DELIVERY|SERVICE|DOCUMENTATION
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # CRITICAL|HIGH|MEDIUM|LOW
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Investigation
    investigation_findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Resolution
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Follow-up
    customer_satisfaction: Mapped[str | None] = mapped_column(String(16), nullable=True)  # SATISFIED|NEUTRAL|UNSATISFIED
    follow_up_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Workflow
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)  # OPEN|INVESTIGATING|RESOLVED|CLOSED
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM", nullable=False)
    
    # Links
    ncr_id: Mapped[str | None] = mapped_column(ForeignKey("qms_ncr.id"), nullable=True)
    capa_id: Mapped[str | None] = mapped_column(ForeignKey("qms_capa.id"), nullable=True)
    
    attachments: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    ncr: Mapped[QMSNCR | None] = relationship()
    capa: Mapped[QMSCAPA | None] = relationship()

# ============================================================================
# Backward compatibility exports (API import stability)
# ============================================================================
# API layer expects generic names:
#   InspectionPlan, Inspection, InspectionResult
# Canonical models in this module are QMS-prefixed.
InspectionPlan = QMSInspectionPlan
Inspection = QMSInspection
InspectionResult = QMSInspectionResult

