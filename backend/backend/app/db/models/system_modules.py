from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, JSON, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt

class SysModule(Base, HasId, HasCreatedAt):
    """Module catalog (what exists in the packaged build)."""
    __tablename__ = "sys_module"

    module_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="0.0.0")
    installed_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    description: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    dependencies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    is_packaged: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_installable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # global installed flag (in multi-tenant this means schema/migrations applied)
    installed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    installed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    upgraded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    upgraded_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_sys_module_installed", SysModule.installed)


class SysTenantModule(Base, HasId, HasCreatedAt):
    """Per-tenant enable/disable for a module."""
    __tablename__ = "sys_tenant_module"

    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="default")
    module_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "module_key", name="uq_tenant_module"),
    )

Index("ix_sys_tenant_module_enabled", SysTenantModule.tenant_id, SysTenantModule.enabled)
