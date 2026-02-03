from __future__ import annotations

import asyncio

from fastapi import FastAPI, Depends
from app.core.module_runtime import set_app
from app.core.module_loader import ensure_mounted
from app.core.middleware import TenantMiddleware
from app.core.audit_middleware import audit_http_middleware
from app.db.base import Base
from app.db.session import engine

# Register models
from app.db import models  # noqa: F401

from services.auth.api import router as auth_router
from services.email_engine.api import router as email_router, tracking_router as email_tracking_router
from services.inventory.api import router as erp_inventory_router
from services.inventory_ops.api import router as inventory_router
from services.sales.api import router as sales_router
from services.purchasing.api import router as purchasing_router
from services.accounting.api import router as accounting_router
from services.qms.api import router as qms_router
from services.mrp.api import router as mrp_router
from services.planning.api import router as planning_router
from services.admin.modules_api import router as modules_router
from services.admin.events_api import router as events_admin_router
from services.mes.api import router as mes_router
from services.admin.module_guard import require_module_enabled
from services.docs.api import router as docs_router
from services.wms.tasking.api import router as tasks_router
from services.wms.control_api import router as wms_control_router
from services.wms.inventory_ops.wave_api import router as waves_router
from services.crm.api import router as crm_router
from services.employee.api import router as employee_router
from services.ecommerce.api import router as ecommerce_router
from services.mdm.api import router as mdm_router
from services.tasking.exceptions_api import router as exceptions_router
from services.inventory_ops.count_review_api import router as counts_router


app = FastAPI(title="Enterprise Standalone + WMS")
set_app(app)
app.add_middleware(TenantMiddleware)

@app.middleware("http")
async def _audit(request, call_next):
    return await audit_http_middleware(request, call_next)

app.include_router(auth_router)
app.include_router(email_router)
app.include_router(email_tracking_router)

@app.on_event("startup")
async def _startup():
    # Dev-friendly schema creation (migrations are available for real upgrades)
    Base.metadata.create_all(bind=engine)

    # Hot-load enabled modules' routers at startup (no restart needed after enabling later).
    from app.db.session import SessionLocal
    from app.db.models.system_modules import SysTenantModule
    with SessionLocal() as db:
        enabled = db.query(SysTenantModule).filter(SysTenantModule.tenant_id=="default", SysTenantModule.enabled==True).all()
        ensure_mounted(app, [r.module_key for r in enabled])

    # Start the lightweight event dispatcher in-process.
    # This makes the event contracts executable without introducing Kafka/NATS yet.
    from app.events.dispatcher import run_dispatcher_forever

    asyncio.create_task(run_dispatcher_forever(poll_interval_seconds=1.0))

app.include_router(mdm_router, dependencies=[Depends(require_module_enabled('mdm'))])
app.include_router(erp_inventory_router, prefix='/erp', dependencies=[Depends(require_module_enabled('inventory'))])
app.include_router(inventory_router, dependencies=[Depends(require_module_enabled('wms'))])
app.include_router(sales_router, dependencies=[Depends(require_module_enabled('sales'))])
app.include_router(purchasing_router, dependencies=[Depends(require_module_enabled('purchasing'))])
app.include_router(accounting_router, dependencies=[Depends(require_module_enabled('accounting'))])
app.include_router(qms_router, dependencies=[Depends(require_module_enabled('qms'))])
app.include_router(mrp_router, dependencies=[Depends(require_module_enabled('mrp'))])
app.include_router(planning_router, dependencies=[Depends(require_module_enabled('planning'))])
app.include_router(modules_router)
app.include_router(events_admin_router)
app.include_router(mes_router)
app.include_router(docs_router, dependencies=[Depends(require_module_enabled('wms'))])
app.include_router(tasks_router, dependencies=[Depends(require_module_enabled('wms'))])
app.include_router(waves_router, dependencies=[Depends(require_module_enabled('wms'))])
app.include_router(exceptions_router, dependencies=[Depends(require_module_enabled('wms'))])
app.include_router(wms_control_router)
app.include_router(counts_router, dependencies=[Depends(require_module_enabled('wms'))])

@app.get("/health")
def health():
    return {"ok": True}

