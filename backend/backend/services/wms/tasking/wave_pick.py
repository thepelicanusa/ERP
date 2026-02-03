from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models.wms.tasking import Task, TaskStep
from services.wms.inventory_ops.wave_optimization import build_wave_pick_plan

def create_wave_pick_task(db: Session, wave_id: str) -> str:
    plan = build_wave_pick_plan(db, wave_id)
    t = Task(type="WAVE_PICK", status="OPEN", context={"wave_id": wave_id, "plan": plan})
    db.add(t); db.flush()

    seq = 5
    # Scan cart (optional)
    db.add(TaskStep(task_id=t.id, seq=seq, kind="SCAN_CONTAINER", prompt="Scan cart", expected={"cart_code": plan.get("cart", {}).get("cart_code")})); seq += 5
    # Scan totes to load onto cart
    for tote in plan.get("totes", []):
        db.add(TaskStep(task_id=t.id, seq=seq, kind="SCAN_CONTAINER", prompt="Scan tote", expected={"tote_code": tote})); seq += 5

    seq = 20
    for stop in plan["stops"]:
        loc_code = stop.get("location_code") or ""
        db.add(TaskStep(task_id=t.id, seq=seq, kind="SCAN_LOCATION", prompt="Scan pick location", expected={"location_code": loc_code}))
        seq += 10
        for ln in stop["lines"]:
            db.add(TaskStep(task_id=t.id, seq=seq, kind="SCAN_ITEM", prompt="Scan item", expected={"sku": ln.get("sku")})); seq += 10
            db.add(TaskStep(task_id=t.id, seq=seq, kind="SCAN_CONTAINER", prompt="Scan destination tote", expected={"tote_code": ln.get("tote_code")})); seq += 10
            db.add(TaskStep(task_id=t.id, seq=seq, kind="ENTER_QTY", prompt=f"Enter qty for order {ln['order_id'][:8]}…", expected={"qty": ln["qty"]})); seq += 10

    db.commit()
    return t.id
