from __future__ import annotations
from sqlalchemy.orm import Session

def commit_refresh(db: Session, obj):
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
