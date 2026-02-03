from __future__ import annotations

"""Shared extraction helpers for the email engine.

These helpers are deliberately kept free of business-module imports so they
can be safely reused across adapters without creating cross-module conflicts.
"""

import re
from decimal import Decimal
from email.utils import parseaddr
from typing import Optional


# Matches "PO 1234", "PO-1234", "PO1234", "P.O. 1234" (conservative)
PO_RE = re.compile(r"\bP\.?\s*O\.?[-\s]*([A-Za-z0-9]{3,32})\b", re.IGNORECASE)

# Very lightweight "total" parser (Phase 1)
TOTAL_RE = re.compile(
    r"(?:(?:invoice\s*)?total|amount\s*due|balance\s*due|grand\s*total)\s*[:\-]?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
    re.IGNORECASE,
)


def email_only(raw_from: str) -> str:
    return (parseaddr(raw_from)[1] or "").strip().lower()


def extract_po_number(text: str) -> Optional[str]:
    if not text:
        return None
    m = PO_RE.search(text)
    if not m:
        return None
    return m.group(1).strip()


def extract_total_amount(text: str) -> Optional[Decimal]:
    """Best-effort total extraction from email/PDF text.

    Intentionally conservative. If no clear total is found, returns None.
    """
    if not text:
        return None
    m = TOTAL_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(",", "").strip()
    try:
        return Decimal(raw)
    except Exception:
        return None
