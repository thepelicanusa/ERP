from __future__ import annotations
from sqlalchemy.orm import Session
from collections import defaultdict
from app.db.models.planning import WaveOrder
from app.db.models.wms.tasking import Task, TaskStep
from app.db.models.inventory_exec import InventoryBalance, Location

def create_consolidated_pick_tasks(db: Session, wave_id: str):
    # One pick task per location, serving multiple orders
    rows = (db.query(WaveOrder)
            .filter(WaveOrder.wave_id == wave_id)
            .all())

    loc_map = defaultdict(list)

    for wo in rows:
        balances = (db.query(InventoryBalance)
                    .join(Location, Location.id == InventoryBalance.location_id)
                    .filter(InventoryBalance.state == "RESERVED")
                    .all())
        for b in balances:
            loc_map[b.location.code].append({
                "order_id": wo.order_id,
                "item_id": b.item_id,
                "qty": float(b.qty)
            })

    tasks = []
    for loc_code, lines in loc_map.items():
        t = Task(type="PICK", status="OPEN", context={
            "mode": "CONSOLIDATED",
            "location_code": loc_code,
            "lines": lines,
        })
        db.add(t); db.flush()
        db.add(TaskStep(task_id=t.id, seq=10, kind="SCAN_LOCATION", prompt="Scan pick location", expected={"location_code": loc_code}))
        db.add(TaskStep(task_id=t.id, seq=20, kind="CONFIRM_LINES", prompt="Confirm picked lines", expected={"lines": lines}))
        tasks.append(t.id)

    db.commit()
    return tasks
