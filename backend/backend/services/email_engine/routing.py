from __future__ import annotations

import re
from typing import Optional

TOKEN_RE = re.compile(r"\[ERP:MSG_([0-9a-fA-F\-]{8,})\]")

def make_correlation_token(msg_uuid: str) -> str:
    return f"MSG_{msg_uuid}"

def embed_token_in_subject(subject: str, msg_uuid: str) -> str:
    token = f"[ERP:MSG_{msg_uuid}]"
    if token in subject:
        return subject
    return (subject or "").strip() + " " + token

def extract_token(text: str) -> Optional[str]:
    if not text:
        return None
    m = TOKEN_RE.search(text)
    if not m:
        return None
    return "MSG_" + m.group(1)

def compute_thread_key(from_email: str, subject: str) -> str:
    # starter thread heuristic; you can improve later
    base = (subject or "").strip().lower()
    base = re.sub(r"^(re:|fw:|fwd:)\s*", "", base).strip()
    return f"{from_email.lower()}::{base[:80]}"
