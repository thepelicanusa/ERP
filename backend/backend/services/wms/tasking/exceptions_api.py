from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal
from app.db.models.wms.tasking import TaskException
from services.wms.inventory_ops.allocation_service import allocate_order

router = APIRouter(prefix="/exceptions", tags=["exceptions"])

@router.get("")
def list_exceptions(kind: str | None = None, status: str | None = "OPEN", db: Session = Depends(get_db), p=Depends(get_principal)):
    q = db.query(TaskException)
    if kind:
        q = q.filter(TaskException.kind == kind)
    if status:
        q = q.filter(TaskException.status == status)
    rows = q.order_by(TaskException.created_at.desc()).limit(200).all()
    return [{"id": e.id, "kind": e.kind, "status": e.status, "task_id": e.task_id, "data": e.data} for e in rows]

@router.post("/{exception_id}/resolve")
def resolve(exception_id: str, payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    e = db.query(TaskException).filter(TaskException.id == exception_id).first()
    if not e:
        raise HTTPException(404, "Exception not found")
    if e.status != "OPEN":
        return {"ok": True, "status": e.status}

    # For SHORT_PICK, we re-run allocation for the order to try to cover remaining qty (best-effort)
    if e.kind == "SHORT_PICK":
        order_id = (e.data or {}).get("order_id")
        if order_id:
            allocate_order(db, order_id)
    e.status = "RESOLVED"
    db.commit()
    return {"ok": True, "status": e.status}
