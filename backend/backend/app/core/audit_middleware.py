from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response

from app.core.tenant import get_tenant_id
from app.core.security import get_principal
from app.db.session import SessionLocal
from app.core.audit import audit


def _get_request_id(request: Request) -> str:
    rid = request.headers.get("X-Request-Id") or request.headers.get("X-Request-ID")
    if rid:
        return rid
    return str(uuid.uuid4())


def _client_ip(request: Request) -> str | None:
    # If behind a proxy/load balancer, you can trust X-Forwarded-For (configure accordingly).
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def audit_http_middleware(request: Request, call_next: Callable) -> Response:
    """Governance-grade audit middleware.

    - Adds a correlation id (X-Request-Id)
    - Logs auth/security events and authorization failures
    """
    request_id = _get_request_id(request)
    start = time.perf_counter()
    tenant_id = request.headers.get("X-Tenant-Id") or get_tenant_id()

    # Run request
    response: Response
    try:
        response = await call_next(request)
    except Exception:
        # Capture unhandled errors as audit events
        duration_ms = int((time.perf_counter() - start) * 1000)
        with SessionLocal() as db:
            audit(
                db,
                actor="anonymous",
                action="http.exception",
                entity_type="http",
                entity_id=request.url.path,
                payload={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
                request_id=request_id,
                ip_address=_client_ip(request),
                user_agent=request.headers.get("User-Agent"),
                status_code=500,
                success=False,
                tenant_id=tenant_id,
            )
        raise

    # Attach request id to response
    response.headers["X-Request-Id"] = request_id

    status_code = response.status_code
    duration_ms = int((time.perf_counter() - start) * 1000)

    # Decide when to log.
    # 1) Always log /auth activity.
    # 2) Log all 401/403 (authz failures) across the platform.
    should_log = request.url.path.startswith("/auth") or status_code in (401, 403)

    if should_log:
        # Decode principal if possible (no Depends in middleware)
        authz = request.headers.get("Authorization")
        actor = "anonymous"
        try:
            if authz and authz.lower().startswith("bearer "):
                token = authz.split(" ", 1)[1].strip()
                with SessionLocal() as db:
                    # Reuse security.get_principal logic by crafting a minimal creds-like object
                    class _Creds:
                        credentials = token

                    principal = get_principal(_Creds(), db)  # type: ignore
                    if principal and principal.user_id:
                        actor = principal.username
        except Exception:
            actor = "anonymous"

        with SessionLocal() as db:
            audit(
                db,
                actor=actor,
                action="http.request",
                entity_type="http",
                entity_id=request.url.path,
                payload={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
                request_id=request_id,
                ip_address=_client_ip(request),
                user_agent=request.headers.get("User-Agent"),
                status_code=status_code,
                success=200 <= status_code < 400,
                tenant_id=tenant_id,
            )

    return response
