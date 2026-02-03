from __future__ import annotations

import enum
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base

class PartyType(str, enum.Enum):
    PERSON = "PERSON"
    ORG = "ORG"

class ContactMethodType(str, enum.Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    OTHER = "OTHER"

class PartyRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"

class LegalEntity(Base):
    __tablename__ = "legal_entity"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    code = Column(String(32), nullable=False)
    name = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_legal_entity_tenant_code"),
    )

class Party(Base):
    __tablename__ = "party"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    party_type = Column(Enum(PartyType), nullable=False)
    display_name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255), nullable=True)
    tax_id = Column(String(64), nullable=True, index=True)
    website = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    profiles = relationship("PartyProfile", back_populates="party")

class PartyProfile(Base):
    __tablename__ = "party_profile"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    legal_entity_id = Column(String(36), ForeignKey("legal_entity.id"), nullable=False, index=True)
    party_id = Column(String(36), ForeignKey("party.id"), nullable=False, index=True)

    status = Column(String(32), default="ACTIVE", nullable=False)
    account_owner_user_id = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    party = relationship("Party", back_populates="profiles")
    roles = relationship("PartyProfileRole", back_populates="profile", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("legal_entity_id", "party_id", name="uq_party_profile_legal_entity_party"),
        Index("ix_party_profile_tenant_legal_entity_party", "tenant_id", "legal_entity_id", "party_id"),
    )

class PartyProfileRole(Base):
    __tablename__ = "party_profile_role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    party_profile_id = Column(String(36), ForeignKey("party_profile.id"), nullable=False, index=True)
    role = Column(Enum(PartyRole), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship("PartyProfile", back_populates="roles")

    __table_args__ = (
        UniqueConstraint("party_profile_id", "role", name="uq_party_profile_role"),
    )

class CustomerProfile(Base):
    __tablename__ = "customer_profile"
    party_profile_id = Column(String(36), ForeignKey("party_profile.id"), primary_key=True)
    payment_terms = Column(String(64), nullable=True)
    credit_limit = Column(Float, nullable=True)

class VendorProfile(Base):
    __tablename__ = "vendor_profile"
    party_profile_id = Column(String(36), ForeignKey("party_profile.id"), primary_key=True)
    payment_terms = Column(String(64), nullable=True)

class PartyContactMethod(Base):
    __tablename__ = "party_contact_method"

    id = Column(Integer, primary_key=True, autoincrement=True)
    party_id = Column(String(36), ForeignKey("party.id"), nullable=False, index=True)
    type = Column(Enum(ContactMethodType), nullable=False)
    label = Column(String(64), nullable=True)
    value = Column(String(255), nullable=False, index=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class PartyAddress(Base):
    __tablename__ = "party_address"

    id = Column(Integer, primary_key=True, autoincrement=True)
    party_id = Column(String(36), ForeignKey("party.id"), nullable=False, index=True)
    label = Column(String(64), nullable=True)
    line1 = Column(String(255), nullable=False)
    line2 = Column(String(255), nullable=True)
    city = Column(String(128), nullable=True)
    region = Column(String(128), nullable=True)
    postal_code = Column(String(32), nullable=True)
    country = Column(String(2), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class RelationshipType(str, enum.Enum):
    EMPLOYEE_OF = "EMPLOYEE_OF"
    CONTACT_FOR = "CONTACT_FOR"
    RELATED = "RELATED"

class PartyRelationship(Base):
    __tablename__ = "party_relationship"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    party_id = Column(String(36), ForeignKey("party.id"), nullable=False, index=True)
    related_party_id = Column(String(36), ForeignKey("party.id"), nullable=False, index=True)

    relationship_type = Column(Enum(RelationshipType), nullable=False)
    strength = Column(Integer, default=50, nullable=False)  # 0-100
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_party_relationship_tenant_party_related", "tenant_id", "party_id", "related_party_id"),
    )
