from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal
from services.wms.tasking.service import get_my_tasks, get_task_with_steps, complete_step

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/my")
def my_tasks(db: Session = Depends(get_db), p=Depends(get_principal)):
    tasks = get_my_tasks(db, assignee=p.username)
    return [{"id": t.id, "type": t.type, "status": t.status, "priority": t.priority, "source_type": t.source_type, "source_id": t.source_id} for t in tasks]

@router.get("/{task_id}")
def task_detail(task_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    task, steps = get_task_with_steps(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return {
        "task": {"id": task.id, "type": task.type, "status": task.status, "context": task.context},
        "steps": [{"id": s.id, "seq": s.seq, "kind": s.kind, "prompt": s.prompt, "expected": s.expected, "status": s.status, "captured": s.captured} for s in steps]
    }

@router.post("/{task_id}/steps/{step_id}/complete")
def step_complete(task_id: str, step_id: str, payload: dict, db: Session = Depends(get_db), p=Depends(get_principal)):
    task, step = complete_step(db, task_id=task_id, step_id=step_id, value=payload.get("value"), actor=p.username, reason=payload.get("reason"))
    return {"task_status": task.status, "step_status": step.status}
