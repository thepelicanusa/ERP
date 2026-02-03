from __future__ import annotations

import json
import os
from datetime import datetime
import subprocess
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_principal
from app.db.models.system_modules import SysModule, SysTenantModule
from app.core.module_runtime import get_app
from app.core.module_loader import mount_module

router = APIRouter(prefix="/admin/modules", tags=["admin_modules"])

MANIFEST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "app", "modules")

def _load_manifests() -> list[dict]:
    out = []
    if not os.path.isdir(MANIFEST_DIR):
        return out
    for fn in os.listdir(MANIFEST_DIR):
        if not fn.endswith(".manifest.json"):
            continue
        with open(os.path.join(MANIFEST_DIR, fn), "r", encoding="utf-8") as f:
            out.append(json.load(f))
    out.sort(key=lambda x: x.get("key",""))
    return out

def _ensure_catalog(db: Session) -> None:
    manifests = _load_manifests()
    for m in manifests:
        key = m["key"]
        mod = db.query(SysModule).filter(SysModule.module_key == key).first()
        if not mod:
            mod = SysModule(
                module_key=key,
                display_name=m.get("name", key),
                version=m.get("version", "0.0.0"),
                description=m.get("description",""),
                dependencies=m.get("depends_on", []),
                is_packaged=True,
                is_installable=bool(m.get("installable", True)),
                installed=False,
                meta={"seeders": m.get("seeders", [])},
            )
            db.add(mod)
        else:
            # keep installed flag, refresh metadata
            mod.display_name = m.get("name", mod.display_name)
            mod.version = m.get("version", mod.version)
            mod.dependencies = m.get("depends_on", mod.dependencies)
            mod.meta = {**(mod.meta or {}), "seeders": m.get("seeders", [])}
    db.commit()

def _require_admin(principal) -> None:
    roles = set(principal.roles or [])
    if "ADMIN" not in roles:
        raise HTTPException(403, "ADMIN role required")

def _get_tenant_id() -> str:
    # Standalone: single tenant
    return "default"

@router.get("")
def list_modules(db: Session = Depends(get_db), principal=Depends(get_principal)):
    _ensure_catalog(db)
    tenant_id = _get_tenant_id()

    mods = db.query(SysModule).order_by(SysModule.module_key.asc()).all()
    enabled_rows = db.query(SysTenantModule).filter(SysTenantModule.tenant_id == tenant_id).all()
    enabled_map = {r.module_key: r for r in enabled_rows}

    out = []
    for m in mods:
        tr = enabled_map.get(m.module_key)
        out.append({
            "module_key": m.module_key,
            "name": m.display_name,
            "version": m.version,
            "dependencies": m.dependencies or [],
            "installed": bool(m.installed),
                "installed_version": m.installed_version,
            "enabled": bool(tr.enabled) if tr else False,
            "installable": bool(m.is_installable),
            "seeders": (m.meta or {}).get("seeders", []),
        })
    return out

def _check_deps_installed(db: Session, module: SysModule) -> None:
    deps = module.dependencies or []
    if not deps:
        return
    missing = []
    for d in deps:
        dm = db.query(SysModule).filter(SysModule.module_key == d).first()
        if not dm or not dm.installed:
            missing.append(d)
    if missing:
        raise HTTPException(409, f"Missing installed dependencies: {missing}")

def _check_deps_enabled(db: Session, tenant_id: str, module: SysModule) -> None:
    deps = module.dependencies or []
    if not deps:
        return
    missing = []
    for d in deps:
        tr = db.query(SysTenantModule).filter(SysTenantModule.tenant_id==tenant_id, SysTenantModule.module_key==d).first()
        if not tr or not tr.enabled:
            missing.append(d)
    if missing:
        raise HTTPException(409, f"Dependencies must be enabled first: {missing}")

@router.post("/{module_key}/install")
def install_module(module_key: str, payload: dict | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    _ensure_catalog(db)

    mod = db.query(SysModule).filter(SysModule.module_key == module_key).first()
    if not mod:
        raise HTTPException(404, "Unknown module_key")
    if not mod.is_installable:
        raise HTTPException(409, "Module is not installable in this build")

    if mod.installed:
        return {"ok": True, "module_key": module_key, "installed": True, "note": "already installed"}

    _check_deps_installed(db, mod)

    # Run Alembic migrations for real upgrades
    env = os.environ.copy()
    env["DATABASE_URL"] = os.getenv("DATABASE_URL", "")
    try:
        subprocess.check_call(
            ["alembic", "-c", "alembic.ini", "upgrade", "head"],
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
            env=env,
        )
    except Exception as e:
        raise HTTPException(500, f"Alembic upgrade failed: {e}")

    mod.installed_version = mod.version
    mod.installed_at = datetime.utcnow()
    mod.installed_by = getattr(principal, "username", None) or "admin"

    db.commit()
    return {"ok": True, "module_key": module_key, "installed": True}

@router.post("/{module_key}/enable")
def enable_module(module_key: str, payload: dict | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    _ensure_catalog(db)
    tenant_id = _get_tenant_id()

    mod = db.query(SysModule).filter(SysModule.module_key == module_key).first()
    if not mod:
        raise HTTPException(404, "Unknown module_key")
    if not mod.installed:
        raise HTTPException(409, "Module must be installed first")

    _check_deps_enabled(db, tenant_id, mod)

    tr = db.query(SysTenantModule).filter(SysTenantModule.tenant_id==tenant_id, SysTenantModule.module_key==module_key).first()
    if not tr:
        tr = SysTenantModule(tenant_id=tenant_id, module_key=module_key, enabled=True, enabled_at=datetime.utcnow(), enabled_by=principal.username, settings={})
        db.add(tr)
    else:
        tr.enabled = True
        tr.enabled_at = datetime.utcnow()
        tr.enabled_by = principal.username

    db.commit()

    # Hot-load: mount the module's router into the running app immediately.
    app = get_app()
    if app is not None:
        try:
            mount_module(app, module_key)
        except Exception:
            # If the module has no router mapping yet (or import fails), keep enable semantics.
            pass

    return {"ok": True, "module_key": module_key, "enabled": True}

@router.post("/{module_key}/disable")
def disable_module(module_key: str, payload: dict | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    _ensure_catalog(db)
    tenant_id = _get_tenant_id()

    tr = db.query(SysTenantModule).filter(SysTenantModule.tenant_id==tenant_id, SysTenantModule.module_key==module_key).first()
    if not tr:
        # already disabled
        return {"ok": True, "module_key": module_key, "enabled": False}

    tr.enabled = False
    tr.enabled_at = datetime.utcnow()
    tr.enabled_by = principal.username
    db.commit()
    return {"ok": True, "module_key": module_key, "enabled": False}

@router.post("/{module_key}/seed/{seed_key}")
def seed_module(module_key: str, seed_key: str, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    _ensure_catalog(db)
    tenant_id = _get_tenant_id()

    mod = db.query(SysModule).filter(SysModule.module_key == module_key).first()
    if not mod or not mod.installed:
        raise HTTPException(409, "Module must be installed first")
    tr = db.query(SysTenantModule).filter(SysTenantModule.tenant_id==tenant_id, SysTenantModule.module_key==module_key).first()
    if not tr or not tr.enabled:
        raise HTTPException(409, "Module must be enabled first")

    # Only implement a safe, deterministic demo seed.
    if module_key == "wms" and seed_key == "default_locations":
        from app.db.models.inventory_exec import WMSLocation
        defaults = [
            ("RECV", "RECEIVE"),
            ("STAGE", "STAGING"),
            ("PACK", "PACK"),
            ("SHIP", "SHIP"),
            ("QA_HOLD", "QUARANTINE"),
        ]
        created = 0
        for code, typ in defaults:
            existing = db.query(WMSLocation).filter(WMSLocation.code == code).first()
            if not existing:
                db.add(WMSLocation(code=code, type=typ, meta={}))
                created += 1
        db.commit()
        return {"ok": True, "seeded": seed_key, "created": created}

    if module_key == "mdm" and seed_key == "demo_bootstrap":
        from app.db.models.mdm import MDMOrgUnit, MDMUoM, MDMItemClass, MDMItem, MDMParty

        created = {"org_units":0, "uoms":0, "item_classes":0, "items":0, "parties":0}

        # Minimal ISA-95 hierarchy
        ent = db.query(MDMOrgUnit).filter(MDMOrgUnit.type=="ENTERPRISE", MDMOrgUnit.code=="ENT1").first()
        if not ent:
            ent = MDMOrgUnit(type="ENTERPRISE", code="ENT1", name="Default Enterprise")
            db.add(ent); db.commit(); db.refresh(ent)
            created["org_units"] += 1

        site = db.query(MDMOrgUnit).filter(MDMOrgUnit.type=="SITE", MDMOrgUnit.code=="SITE1").first()
        if not site:
            site = MDMOrgUnit(type="SITE", code="SITE1", name="Main Site", parent_id=ent.id)
            db.add(site); db.commit(); db.refresh(site)
            created["org_units"] += 1

        area = db.query(MDMOrgUnit).filter(MDMOrgUnit.type=="AREA", MDMOrgUnit.code=="AREA1").first()
        if not area:
            area = MDMOrgUnit(type="AREA", code="AREA1", name="Production", parent_id=site.id)
            db.add(area); db.commit(); db.refresh(area)
            created["org_units"] += 1

        line = db.query(MDMOrgUnit).filter(MDMOrgUnit.type=="LINE", MDMOrgUnit.code=="LINE1").first()
        if not line:
            line = MDMOrgUnit(type="LINE", code="LINE1", name="Line 1", parent_id=area.id)
            db.add(line); db.commit(); db.refresh(line)
            created["org_units"] += 1

        cell = db.query(MDMOrgUnit).filter(MDMOrgUnit.type=="CELL", MDMOrgUnit.code=="CELL1").first()
        if not cell:
            cell = MDMOrgUnit(type="CELL", code="CELL1", name="Cell 1", parent_id=line.id)
            db.add(cell); db.commit(); db.refresh(cell)
            created["org_units"] += 1

        # UoM
        ea = db.query(MDMUoM).filter(MDMUoM.code=="EA").first()
        if not ea:
            ea = MDMUoM(code="EA", name="Each")
            db.add(ea); db.commit(); db.refresh(ea)
            created["uoms"] += 1

        # Item class
        fg = db.query(MDMItemClass).filter(MDMItemClass.code=="FG").first()
        if not fg:
            fg = MDMItemClass(code="FG", name="Finished Good")
            db.add(fg); db.commit(); db.refresh(fg)
            created["item_classes"] += 1

        # Item
        item = db.query(MDMItem).filter(MDMItem.item_code=="ITEM-001").first()
        if not item:
            item = MDMItem(item_code="ITEM-001", name="Demo Item", uom_id=ea.id, class_id=fg.id)
            db.add(item); db.commit(); db.refresh(item)
            created["items"] += 1

        # Parties
        vend = db.query(MDMParty).filter(MDMParty.code=="VEND-001").first()
        if not vend:
            vend = MDMParty(party_type="VENDOR", code="VEND-001", name="Demo Vendor")
            db.add(vend); db.commit();
            created["parties"] += 1
        cust = db.query(MDMParty).filter(MDMParty.code=="CUST-001").first()
        if not cust:
            cust = MDMParty(party_type="CUSTOMER", code="CUST-001", name="Demo Customer")
            db.add(cust); db.commit();
            created["parties"] += 1

        return {"ok": True, "seeded": seed_key, "created": created}

    raise HTTPException(404, "Unknown seed key for this module")

@router.post("/{module_key}/upgrade")
def upgrade_module(module_key: str, payload: dict | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    _ensure_catalog(db)

    mod = db.query(SysModule).filter(SysModule.module_key == module_key).first()
    if not mod:
        raise HTTPException(404, "Unknown module_key")
    if not mod.is_installable:
        raise HTTPException(409, "Module is not installable in this build")
    if not mod.installed:
        raise HTTPException(409, "Module must be installed first")

    _check_deps_installed(db, mod)

    # Run Alembic migrations for real upgrades
    env = os.environ.copy()
    env["DATABASE_URL"] = os.getenv("DATABASE_URL", "")
    try:
        subprocess.check_call(
            ["alembic", "-c", "alembic.ini", "upgrade", "head"],
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
            env=env,
        )
    except Exception as e:
        raise HTTPException(500, f"Alembic upgrade failed: {e}")

    mod.installed_version = mod.version
    mod.upgraded_at = datetime.utcnow()
    mod.upgraded_by = getattr(principal, "username", None) or "admin"
    db.commit()
    return {"ok": True, "module_key": module_key, "upgraded": True, "installed_version": mod.installed_version}
