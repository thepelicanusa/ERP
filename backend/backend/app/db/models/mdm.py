from __future__ import annotations

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt


class MDMOrgUnit(Base, HasId, HasCreatedAt):
    """ISA-95 hierarchy node.

    We model Enterprise/Site/Area/Line/Cell as a single table with a `type` and `parent_id`.

    Ownership rule: this table is the single source of truth for the enterprise hierarchy.
    Other modules reference org units by `mdm_org_unit.id` only.
    """

    __tablename__ = "mdm_org_unit"
    __table_args__ = (
        UniqueConstraint("type", "code", name="uq_mdm_org_unit_type_code"),
    )

    type: Mapped[str] = mapped_column(String(32), nullable=False)  # ENTERPRISE|SITE|AREA|LINE|CELL
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)

    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mdm_org_unit.id"), nullable=True)
    parent: Mapped[Optional["MDMOrgUnit"]] = relationship("MDMOrgUnit", remote_side="MDMOrgUnit.id", backref="children")

    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MDMUoM(Base, HasId, HasCreatedAt):
    __tablename__ = "mdm_uom"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class MDMItemClass(Base, HasId, HasCreatedAt):
    __tablename__ = "mdm_item_class"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)


class MDMItem(Base, HasId, HasCreatedAt):
    __tablename__ = "mdm_item"

    item_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)

    uom_id: Mapped[str] = mapped_column(String(36), ForeignKey("mdm_uom.id"), nullable=False)
    uom: Mapped[MDMUoM] = relationship("MDMUoM")

    class_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mdm_item_class.id"), nullable=True)
    item_class: Mapped[MDMItemClass | None] = relationship("MDMItemClass")

    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    revision: Mapped[str] = mapped_column(String(32), default="A", nullable=False)

    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MDMParty(Base, HasId, HasCreatedAt):
    __tablename__ = "mdm_party"

    party_type: Mapped[str] = mapped_column(String(32), nullable=False)  # CUSTOMER|VENDOR|CARRIER|OTHER
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)


class MDMPerson(Base, HasId, HasCreatedAt):
    __tablename__ = "mdm_person"

    employee_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)

    org_unit_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mdm_org_unit.id"), nullable=True)
    org_unit: Mapped[MDMOrgUnit | None] = relationship("MDMOrgUnit")


class MDMEquipment(Base, HasId, HasCreatedAt):
    __tablename__ = "mdm_equipment"

    equipment_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(64), default="GENERIC", nullable=False)

    org_unit_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mdm_org_unit.id"), nullable=True)
    org_unit: Mapped[MDMOrgUnit | None] = relationship("MDMOrgUnit")
