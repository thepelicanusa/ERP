from __future__ import annotations

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt
from sqlalchemy import String, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List


class User(Base, HasId, HasCreatedAt):
    __tablename__ = "auth_user"

    email: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")


class Role(Base, HasId, HasCreatedAt):
    __tablename__ = "auth_role"

    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=False, default="")

    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")


class Permission(Base, HasId, HasCreatedAt):
    __tablename__ = "auth_permission"

    code: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=False, default="")

    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class UserRole(Base, HasId, HasCreatedAt):
    __tablename__ = "auth_user_role"

    # Multi-tenant + scoped RBAC grant.
    # Scope model is "all-in" from day one:
    #   TENANT / SITE / WAREHOUSE / ZONE / AISLE / LINE / WORKCENTER / WORKSTATION / EQUIPMENT
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), default="TENANT", index=True, nullable=False)
    scope_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("auth_user.id"), index=True, nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("auth_role.id"), index=True, nullable=False)

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")

    __table_args__ = (
        Index(
            "uq_auth_user_role_grant",
            "tenant_id",
            "user_id",
            "role_id",
            "scope_type",
            "scope_id",
            unique=True,
        ),
    )


class RolePermission(Base, HasId, HasCreatedAt):
    __tablename__ = "auth_role_permission"

    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("auth_role.id"), index=True, nullable=False)
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("auth_permission.id"), index=True, nullable=False)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

    __table_args__ = (
        Index("uq_auth_role_perm_role_perm", "role_id", "permission_id", unique=True),
    )

# =============================================================================
# Relationship disambiguation: two UserRole classes exist (auth.py + wms/controls.py).
# SQLAlchemy requires module-qualified paths to avoid _MultipleClassMarker.
# =============================================================================
try:
    # Rebind relationships to the auth-scoped UserRole explicitly.
    User.roles.property.argument = "app.db.models.auth.UserRole"
    Role.users.property.argument = "app.db.models.auth.UserRole"
except Exception:
    # If properties aren't initialized yet during import, ignore.
    pass
