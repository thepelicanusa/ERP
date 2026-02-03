from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.security_audit import AuditLog
from app.core.tenant import get_tenant_id


def audit(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    payload: dict | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    status_code: int | None = None,
    success: bool = True,
    tenant_id: str | None = None,
) -> None:
    """Write an append-only audit record.

    Keep payload JSON-serializable.
    """
    tenant_id = tenant_id or get_tenant_id()
    safe_payload: dict[str, Any] = payload or {}
    try:
        # Ensure it can roundtrip to JSON (avoids runtime errors on commit)
        json.dumps(safe_payload, default=str)
    except Exception:
        safe_payload = {"_payload_error": "non_json", "_payload_repr": repr(payload)}

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status_code=status_code,
            success=success,
            payload=safe_payload,
        )
    )
    db.commit()
