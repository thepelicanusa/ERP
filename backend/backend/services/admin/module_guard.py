from __future__ import annotations
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.system_modules import SysTenantModule

from app.core.tenant import get_tenant_id as _get

def get_tenant_id() -> str:
    return _get()

def require_module_enabled(module_key: str):
    def _dep(db: Session = Depends(get_db)):
        tenant_id = get_tenant_id()
        tr = db.query(SysTenantModule).filter(
            SysTenantModule.tenant_id == tenant_id,
            SysTenantModule.module_key == module_key,
        ).first()
        if not tr or not tr.enabled:
            # Use 404 so disabled modules "disappear" from API surface
            raise HTTPException(status_code=404, detail=f"Module '{module_key}' is not enabled")
    return _dep
