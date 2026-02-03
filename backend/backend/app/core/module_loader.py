from __future__ import annotations

import importlib
from typing import Any, Callable, Dict, Optional, Tuple

from fastapi import FastAPI

from services.admin.module_guard import require_module_enabled

# Module -> (import_path, router_attr, prefix)
# Keep this map as the single source of truth for optional modules.
MODULE_ROUTERS: Dict[str, Tuple[str, str, str]] = {
    "mdm": ("services.mdm.api", "router", ""),
    "inventory": ("services.inventory.api", "router", "/erp"),  # mounted with /erp prefix in main today
    "wms": ("services.inventory_ops.api", "router", ""),
    "sales": ("services.sales.api", "router", ""),
    "purchasing": ("services.purchasing.api", "router", ""),
    "accounting": ("services.accounting.api", "router", ""),
    "qms": ("services.qms.api", "router", ""),
    "mrp": ("services.mrp.api", "router", ""),
    "planning": ("services.planning.api", "router", ""),
    "mes": ("services.mes.api", "router", ""),
    "ecommerce": ("services.ecommerce.api", "router", ""),
    "crm": ("services.crm.api", "router", ""),
    "employee": ("services.employee.api", "router", ""),
    "tasking": ("services.tasking.exceptions_api", "router", ""),  # guarded under wms elsewhere; keep optional
    "docs": ("services.docs.api", "router", ""),  # often wms-only
    "contacts": ("services.contacts.api", "router", ""),
    "support": ("services.support.api", "router", ""),
}

# Tracks what we already mounted to keep idempotent behavior.
_mounted: set[str] = set()

def mount_module(app: FastAPI, module_key: str) -> bool:
    """Mount a module router into the running app.

    Returns True if mounted now, False if already mounted or unknown.
    Safe to call multiple times.
    """
    if module_key in _mounted:
        return False
    spec = MODULE_ROUTERS.get(module_key)
    if not spec:
        return False

    import_path, router_attr, prefix = spec
    mod = importlib.import_module(import_path)
    router = getattr(mod, router_attr)

    deps = [require_module_enabled(module_key)]
    if prefix:
        app.include_router(router, prefix=prefix, dependencies=deps)
    else:
        app.include_router(router, dependencies=deps)

    _mounted.add(module_key)
    return True

def ensure_mounted(app: FastAPI, module_keys: list[str]) -> None:
    for k in module_keys:
        mount_module(app, k)
