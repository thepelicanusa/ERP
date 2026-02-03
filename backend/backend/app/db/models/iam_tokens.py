from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt


class RefreshToken(Base, HasId, HasCreatedAt):
    """Persisted refresh tokens.

    Access tokens are short-lived JWTs. Refresh tokens are stored server-side so we can:
      - revoke sessions
      - rotate refresh tokens
      - audit logouts / token refresh
    """

    __tablename__ = "auth_refresh_token"

    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)


Index("ix_refresh_token_tenant_user", RefreshToken.tenant_id, RefreshToken.user_id)


class RevokedJTI(Base, HasId, HasCreatedAt):
    """Optional access-token revocation list (by JWT ID)."""

    __tablename__ = "auth_revoked_jti"

    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


Index("ix_revoked_jti_tenant_time", RevokedJTI.tenant_id, RevokedJTI.revoked_at)
