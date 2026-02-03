from __future__ import annotations

import os, hashlib
from typing import Tuple

ATTACH_DIR = os.getenv("EMAIL_ATTACH_DIR", "/var/lib/erp/attachments")

def ensure_dir() -> None:
    os.makedirs(ATTACH_DIR, exist_ok=True)

def save_attachment(content: bytes, filename: str) -> Tuple[str, str]:
    """
    Returns (storage_path, sha256)
    """
    ensure_dir()
    sha = hashlib.sha256(content).hexdigest()
    safe_name = filename.replace("/", "_").replace("..", "_")
    path = os.path.join(ATTACH_DIR, f"{sha}_{safe_name}")
    with open(path, "wb") as f:
        f.write(content)
    return path, sha


def read_attachment(storage_path: str) -> bytes:
    # Minimal helper; assumes storage_path is one we generated.
    with open(storage_path, "rb") as f:
        return f.read()
