from __future__ import annotations

"""Integration registry for the email engine.

Purpose:
  - Keep email engine core independent from AP/Sales/etc.
  - Allow optional adapters to register handlers.

The email engine calls into this registry when it wants to "auto-create"
business documents from an inbound email.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class InboundEmailContext:
    owner_user_name: str
    from_email: str
    subject: str
    body_text: str
    attachment_text: str


@dataclass(frozen=True)
class CreatedLink:
    erp_model: str
    erp_record_id: str
    obj: object


# Handler returns a CreatedLink (or None)
Handler = Callable[[Session, InboundEmailContext], Optional[CreatedLink]]

_handlers: Dict[str, List[Handler]] = {"ap": [], "sales": []}
_defaults_loaded = False


def register(kind: str, handler: Handler) -> None:
    if kind not in _handlers:
        _handlers[kind] = []
    _handlers[kind].append(handler)


def load_default_adapters() -> None:
    """Load built-in adapters (best-effort).

    Adapters may fail to import if a business module isn't installed.
    That's OK: the email engine still works and will route to triage.
    """
    global _defaults_loaded
    if _defaults_loaded:
        return
    _defaults_loaded = True

    # AP adapter
    try:
        from .adapters import ap as ap_adapter

        def _ap_handler(db: Session, ctx: InboundEmailContext) -> Optional[CreatedLink]:
            inv = ap_adapter.try_create_ap_invoice_from_email(
                db=db,
                owner_user_name=ctx.owner_user_name,
                from_email=ctx.from_email,
                subject=ctx.subject,
                body_text=ctx.body_text,
                attachment_text=ctx.attachment_text,
            )
            if inv is None:
                return None
            return CreatedLink(erp_model="ap.invoice", erp_record_id=str(inv.id), obj=inv)

        register("ap", _ap_handler)
    except Exception:
        pass

    # Sales adapter
    try:
        from .adapters import sales as sales_adapter

        def _sales_handler(db: Session, ctx: InboundEmailContext) -> Optional[CreatedLink]:
            so = sales_adapter.try_create_sales_order_from_email(
                db=db,
                owner_user_name=ctx.owner_user_name,
                from_email=ctx.from_email,
                subject=ctx.subject,
                body_text=ctx.body_text,
                attachment_text=ctx.attachment_text,
            )
            if so is None:
                return None
            return CreatedLink(erp_model="sales.order", erp_record_id=str(so.id), obj=so)

        register("sales", _sales_handler)
    except Exception:
        pass


def try_auto_create(db: Session, ctx: InboundEmailContext) -> Optional[CreatedLink]:
    """Try handlers in priority order (AP first, then Sales)."""
    load_default_adapters()
    for kind in ("ap", "sales"):
        for h in _handlers.get(kind, []):
            link = h(db, ctx)
            if link is not None:
                return link
    return None
