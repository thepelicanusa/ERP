from __future__ import annotations
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.tenant import set_tenant_id

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant = request.headers.get("X-Tenant-Id") or request.headers.get("x-tenant-id") or "default"
        set_tenant_id(tenant)
        return await call_next(request)
