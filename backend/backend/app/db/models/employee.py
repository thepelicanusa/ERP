from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.common import HasCreatedAt, HasId
from typing import Optional


class Employee(Base, HasId, HasCreatedAt):
    __tablename__ = "hr_employee"

    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    # Identity & profile
    employee_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    legal_first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    legal_last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    legal_middle_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    preferred_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pronouns: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    work_email: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    work_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Emergency contact (v1: single contact)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emergency_contact_relationship: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Region-specific identifiers (PII)
    national_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Right-to-work / visa
    visa_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    visa_expiry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Employment details
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    probation_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)
    contract_type: Mapped[str] = mapped_column(String(32), default="FT", nullable=False)
    fte_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("100.00"), nullable=False)

    job_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    job_grade: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cost_center: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    work_site: Mapped[str | None] = mapped_column(String(128), nullable=True)

    manager_employee_id: Mapped[str | None] = mapped_column(ForeignKey("hr_employee.id"), nullable=True, index=True)
    dotted_manager_employee_id: Mapped[str | None] = mapped_column(
        ForeignKey("hr_employee.id"), nullable=True, index=True
    )

    # Link system user <-> employee
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Compensation (restricted)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    salary_annual: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    manager: Mapped[Optional["Employee"]] = relationship(foreign_keys=[manager_employee_id], remote_side="Employee.id")
    dotted_manager: Mapped[Optional["Employee"]] = relationship(
        foreign_keys=[dotted_manager_employee_id], remote_side="Employee.id"
    )


Index("ix_hr_employee_tenant_code", Employee.tenant_id, Employee.employee_code, unique=True)


class EmployeeDocument(Base, HasId, HasCreatedAt):
    __tablename__ = "hr_employee_document"

    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(ForeignKey("hr_employee.id"), nullable=False, index=True)

    doc_type: Mapped[str] = mapped_column(String(64), default="GENERIC", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    attachment_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    employee: Mapped[Employee] = relationship()


Index("ix_hr_emp_doc_tenant_emp", EmployeeDocument.tenant_id, EmployeeDocument.employee_id)


class EmployeeAsset(Base, HasId, HasCreatedAt):
    __tablename__ = "hr_employee_asset"

    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(ForeignKey("hr_employee.id"), nullable=False, index=True)

    asset_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asset_tag: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    custody_notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    employee: Mapped[Employee] = relationship()


Index("ix_hr_emp_asset_tenant_emp", EmployeeAsset.tenant_id, EmployeeAsset.employee_id)

class EmployeeDocumentTemplate(Base, HasId, HasCreatedAt):
    __tablename__ = "hr_document_template"

    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # e.g. OFFER_LETTER
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), default="GENERIC", nullable=False, index=True)

    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Applicability filters (optional). If None, applies to all.
    contract_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)  # FT/PT/CONTRACTOR
    location: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    expiry_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_expiry_days: Mapped[int | None] = mapped_column(Integer, nullable=True)  # when expiry_required and no expires_at provided

    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_hr_doc_tpl_tenant_key", EmployeeDocumentTemplate.tenant_id, EmployeeDocumentTemplate.key, unique=True)


class EmployeeOffboardingItem(Base, HasId, HasCreatedAt):
    __tablename__ = "hr_employee_offboarding_item"

    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(ForeignKey("hr_employee.id"), nullable=False, index=True)

    item_type: Mapped[str] = mapped_column(String(32), default="TASK", nullable=False, index=True)  # TASK/ASSET
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False, index=True)  # OPEN/DONE/WAIVED

    related_asset_id: Mapped[str | None] = mapped_column(ForeignKey("hr_employee_asset.id"), nullable=True, index=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    waiver_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    employee: Mapped[Employee] = relationship()
