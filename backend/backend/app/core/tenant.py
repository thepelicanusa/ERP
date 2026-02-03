from __future__ import annotations
import contextvars

_tenant: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id", default="default")

def set_tenant_id(tenant_id: str) -> None:
    _tenant.set(tenant_id or "default")

def get_tenant_id() -> str:
    return _tenant.get()
