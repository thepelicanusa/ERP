from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.auth import User, Role, Permission, UserRole, RolePermission
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    mint_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
    get_principal,
    Principal,
    require_permissions,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


def _ensure_seed(db: Session) -> None:
    # Create default roles/permissions if missing.
    default_roles = [
        ("ADMIN", "System administrator"),
        ("AP_CLERK", "Accounts payable clerk"),
        ("AP_MANAGER", "Accounts payable manager"),
        ("SALES_REP", "Sales representative"),
        ("OPERATOR", "Warehouse/MES operator"),
        ("QA", "Quality assurance"),
        ("USER", "Basic user"),
    ]
    for name, desc in default_roles:
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name, description=desc))
    db.flush()

    # Core permissions (extend as needed)
    default_perms = [
        ("auth.role.manage", "Manage roles and permissions"),
        ("auth.user.manage", "Manage users"),
        ("email.account.manage_own", "Manage own email account"),
        ("email.account.manage_any", "Manage any email account"),
        ("email.send", "Send email"),
        ("email.read", "Read email"),
        ("email.triage.view", "View triage"),
        ("email.triage.resolve", "Resolve triage"),
        ("email.triage.attach", "Attach triage to record"),
        ("email.triage.create_ap_invoice", "Create AP invoice from triage"),
        ("email.triage.create_sales_order", "Create sales order from triage"),
        ("ap.invoice.create", "Create AP invoices"),
        ("ap.invoice.approve", "Approve AP invoices"),
        ("sales.order.create", "Create sales orders"),
        ("sales.order.confirm", "Confirm sales orders"),
    ]
    perm_objs = {}
    for code, desc in default_perms:
        p = db.query(Permission).filter(Permission.code == code).first()
        if not p:
            p = Permission(code=code, description=desc)
            db.add(p)
        perm_objs[code] = p
    db.flush()

    # Role -> permissions mapping
    role_map = {
        "ADMIN": [p[0] for p in default_perms],
        "USER": ["email.account.manage_own", "email.send", "email.read", "email.triage.view"],
        "AP_CLERK": ["email.read", "email.triage.view", "email.triage.resolve", "email.triage.attach",
                    "email.triage.create_ap_invoice", "ap.invoice.create"],
        "AP_MANAGER": ["email.read", "email.triage.view", "email.triage.resolve", "email.triage.attach",
                       "email.triage.create_ap_invoice", "ap.invoice.create", "ap.invoice.approve"],
        "SALES_REP": ["email.read", "email.triage.view", "email.triage.resolve", "email.triage.attach",
                      "email.triage.create_sales_order", "sales.order.create", "sales.order.confirm"],
        "QA": ["email.read", "email.triage.view"],
        "OPERATOR": ["email.read"],
    }
    for role_name, perm_codes in role_map.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            continue
        existing = {(rp.permission.code) for rp in role.permissions}
        for code in perm_codes:
            if code in existing:
                continue
            perm = perm_objs.get(code) or db.query(Permission).filter(Permission.code == code).first()
            if perm:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()


@router.post("/seed")
def seed(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    # Only admins should call seed after initial bootstrap.
    if "ADMIN" not in (principal.roles or []):
        raise HTTPException(status_code=403, detail="ADMIN role required")
    _ensure_seed(db)
    return {"ok": True}


@router.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    # Ensure seed exists so we can assign USER role
    _ensure_seed(db)

    # Bootstrap rule: the very first user to register becomes ADMIN.
    # This avoids any manual DB edits on a fresh install.
    is_first_user = db.query(User).count() == 0

    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=payload.email, full_name=payload.full_name or "", password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()

    tenant_id = request.headers.get("X-Tenant-Id") or "default"

    role_name = "ADMIN" if is_first_user else "USER"
    user_role = db.query(Role).filter(Role.name == role_name).first()
    if user_role:
        db.add(
            UserRole(
                tenant_id=tenant_id,
                user_id=user.id,
                role_id=user_role.id,
                scope_type="TENANT",
                scope_id=tenant_id,
            )
        )
    db.commit()

    access = create_access_token(db, user.id, tenant_id=tenant_id)
    refresh = mint_refresh_token(
        db,
        user.id,
        tenant_id=tenant_id,
        created_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return TokenOut(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    _ensure_seed(db)
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    tenant_id = request.headers.get("X-Tenant-Id") or "default"
    access = create_access_token(db, user.id, tenant_id=tenant_id)
    refresh = mint_refresh_token(
        db,
        user.id,
        tenant_id=tenant_id,
        created_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return TokenOut(access_token=access, refresh_token=refresh)


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn, request: Request, db: Session = Depends(get_db)):
    user_id, tenant_id, new_refresh = rotate_refresh_token(
        db,
        payload.refresh_token,
        created_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    access = create_access_token(db, user_id, tenant_id=tenant_id)
    return TokenOut(access_token=access, refresh_token=new_refresh)


class LogoutIn(BaseModel):
    refresh_token: str


@router.post("/logout")
def logout(payload: LogoutIn, db: Session = Depends(get_db)):
    revoke_refresh_token(db, payload.refresh_token)
    return {"ok": True}


@router.get("/me")
def me(principal: Principal = Depends(get_principal)):
    if not principal.user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "user_id": principal.user_id,
        "email": principal.username,
        "tenant_id": principal.tenant_id,
        "roles": principal.roles,
        "permissions": principal.permissions,
        "grants": [
            {
                "role": g.role,
                "scope_type": g.scope_type,
                "scope_id": g.scope_id,
                "perms": g.perms,
            }
            for g in (principal.grants or [])
        ],
    }


class GrantRoleIn(BaseModel):
    user_email: EmailStr
    role_name: str
    tenant_id: str | None = None
    scope_type: str = "TENANT"
    scope_id: str | None = None


@router.post("/grant-role", dependencies=[Depends(require_permissions(["auth.user.manage"]))])
def grant_role(payload: GrantRoleIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = db.query(Role).filter(Role.name == payload.role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    tenant_id = payload.tenant_id or "default"
    scope_id = payload.scope_id or tenant_id
    exists = (
        db.query(UserRole)
        .filter(
            UserRole.tenant_id == tenant_id,
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
            UserRole.scope_type == payload.scope_type,
            UserRole.scope_id == scope_id,
        )
        .first()
    )
    if not exists:
        db.add(
            UserRole(
                tenant_id=tenant_id,
                user_id=user.id,
                role_id=role.id,
                scope_type=payload.scope_type,
                scope_id=scope_id,
            )
        )
        db.commit()
    return {"ok": True}
