from __future__ import annotations

from typing import Optional
from fastapi import FastAPI

_app: Optional[FastAPI] = None

def set_app(app: FastAPI) -> None:
    global _app
    _app = app

def get_app() -> Optional[FastAPI]:
    return _app
