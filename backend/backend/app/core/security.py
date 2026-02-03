from __future__ import annotations

import os
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.auth import User
from app.db.models.iam_tokens import RefreshToken, RevokedJTI
from app.core.tenant import get_tenant_id

bearer = HTTPBearer(auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_TTL_MIN = int(os.getenv("JWT_TTL_MIN", "30"))  # 30m default

IAM_ISSUER = os.getenv("IAM_ISSUER", "enterprise-iam")
IAM_AUDIENCE = os.getenv("IAM_AUDIENCE", "enterprise-core")
REFRESH_TTL_DAYS = int(os.getenv("REFRESH_TTL_DAYS", "14"))


@dataclass
class Grant:
    role: str
    scope_type: str
    scope_id: str
    perms: list[str]


@dataclass
class Principal:
    user_id: str | None = None
    username: str = "anonymous"
    tenant_id: str = "default"
    grants: list[Grant] | None = None

    @property
    def roles(self) -> list[str]:
        return sorted({g.role for g in (self.grants or [])})

    @property
    def permissions(self) -> list[str]:
        perms: set[str] = set()
        for g in (self.grants or []):
            perms.update(g.perms)
        return sorted(perms)

    def has_role(self, role: str, scope_type: str | None = None, scope_id: str | None = None) -> bool:
        for g in (self.grants or []):
            if g.role != role:
                continue
            if scope_type is None and scope_id is None:
                return True
            if scope_type is not None and g.scope_type != scope_type:
                continue
            if scope_id is not None and g.scope_id != scope_id:
                continue
            return True
        return False

    def has_permission(self, perm: str, scope_type: str | None = None, scope_id: str | None = None) -> bool:
        for g in (self.grants or []):
            if perm not in (g.perms or []):
                continue
            if scope_type is None and scope_id is None:
                return True
            if scope_type is not None and g.scope_type != scope_type:
                continue
            if scope_id is not None and g.scope_id != scope_id:
                continue
            return True
        return False


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


def _get_user_grants(db: Session, user_id: str, tenant_id: str) -> tuple[list[Grant], str]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return [], "unknown"

    grants: list[Grant] = []
    for ur in user.roles:
        if ur.tenant_id != tenant_id:
            continue
        role = ur.role
        if not role:
            continue
        perms: list[str] = []
        for rp in role.permissions:
            if rp.permission:
                perms.append(rp.permission.code)
        grants.append(
            Grant(
                role=role.name,
                scope_type=ur.scope_type,
                scope_id=ur.scope_id,
                perms=sorted(set(perms)),
            )
        )

    return grants, user.email


def _make_jti() -> str:
    return secrets.token_urlsafe(16)


def create_access_token(db: Session, user_id: str, tenant_id: str | None = None) -> str:
    tenant_id = tenant_id or get_tenant_id()
    grants, email = _get_user_grants(db, user_id, tenant_id)
    now = datetime.now(timezone.utc)
    jti = _make_jti()
    payload = {
        "iss": IAM_ISSUER,
        "aud": IAM_AUDIENCE,
        "jti": jti,
        "sub": user_id,
        "tid": tenant_id,
        "email": email,
        "grants": [
            {
                "role": g.role,
                "scope_type": g.scope_type,
                "scope_id": g.scope_id,
                "perms": g.perms,
            }
            for g in grants
        ],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_TTL_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def mint_refresh_token(
    db: Session,
    user_id: str,
    tenant_id: str | None = None,
    created_ip: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Create and persist a refresh token; return the raw token string."""
    tenant_id = tenant_id or get_tenant_id()
    raw = secrets.token_urlsafe(48)
    token_hash = _hash_refresh_token(raw)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=REFRESH_TTL_DAYS)
    db.add(
        RefreshToken(
            tenant_id=tenant_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires,
            revoked_at=None,
            created_ip=created_ip,
            user_agent=user_agent,
        )
    )
    db.commit()
    return raw


def rotate_refresh_token(
    db: Session,
    raw_refresh_token: str,
    created_ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str, str]:
    """Validate refresh token, revoke it, and mint a new one.

    Returns (user_id, tenant_id, new_raw_refresh_token).
    """
    token_hash = _hash_refresh_token(raw_refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    now = datetime.now(timezone.utc)
    if not rt or rt.revoked_at is not None or rt.expires_at <= now:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Revoke old token and mint new.
    rt.revoked_at = now
    db.add(rt)
    db.commit()

    new_raw = mint_refresh_token(
        db,
        user_id=rt.user_id,
        tenant_id=rt.tenant_id,
        created_ip=created_ip,
        user_agent=user_agent,
    )
    return rt.user_id, rt.tenant_id, new_raw


def revoke_refresh_token(db: Session, raw_refresh_token: str, reason: str | None = None) -> None:
    token_hash = _hash_refresh_token(raw_refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not rt:
        return
    now = datetime.now(timezone.utc)
    if rt.revoked_at is None:
        rt.revoked_at = now
        db.add(rt)
        db.commit()


def get_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if not creds or not creds.credentials:
        # Anonymous
        return Principal(user_id=None, username="anonymous", tenant_id=get_tenant_id(), grants=[])

    token = creds.credentials
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALG],
            audience=IAM_AUDIENCE,
            issuer=IAM_ISSUER,
        )
        user_id = payload.get("sub")
        email = payload.get("email") or "unknown"
        tenant_id = payload.get("tid") or get_tenant_id()

        # Optional: JTI revocation check
        jti = payload.get("jti")
        if jti:
            revoked = db.query(RevokedJTI).filter(RevokedJTI.jti == jti, RevokedJTI.is_active == True).first()  # noqa: E712
            if revoked:
                return Principal(user_id=None, username="anonymous", tenant_id=tenant_id, grants=[])

        grants_raw = payload.get("grants") or []
        grants: list[Grant] = []
        for g in grants_raw:
            if not isinstance(g, dict):
                continue
            grants.append(
                Grant(
                    role=str(g.get("role")),
                    scope_type=str(g.get("scope_type")),
                    scope_id=str(g.get("scope_id")),
                    perms=list(g.get("perms") or []),
                )
            )
        # Optional: verify user still active
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return Principal(user_id=None, username="anonymous", tenant_id=tenant_id, grants=[])
        return Principal(user_id=user_id, username=email, tenant_id=tenant_id, grants=grants)
    except JWTError:
        return Principal(user_id=None, username="anonymous", tenant_id=get_tenant_id(), grants=[])


def require_roles(required: Iterable[str], scope_type: str | None = None, scope_id: str | None = None) -> Callable:
    required_set = set(required)

    def _dep(principal: Principal = Depends(get_principal)) -> None:
        if not principal.user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        missing = [r for r in required_set if not principal.has_role(r, scope_type=scope_type, scope_id=scope_id)]
        if missing:
            detail = {
                "error": "missing_roles",
                "missing": sorted(missing),
                "scope_type": scope_type,
                "scope_id": scope_id,
            }
            raise HTTPException(status_code=403, detail=detail)

    return _dep


def require_permissions(required: Iterable[str], scope_type: str | None = None, scope_id: str | None = None) -> Callable:
    required_set = set(required)

    def _dep(principal: Principal = Depends(get_principal)) -> None:
        if not principal.user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        missing = [p for p in required_set if not principal.has_permission(p, scope_type=scope_type, scope_id=scope_id)]
        if missing:
            detail = {
                "error": "missing_permissions",
                "missing": sorted(missing),
                "scope_type": scope_type,
                "scope_id": scope_id,
            }
            raise HTTPException(status_code=403, detail=detail)

    return _dep
