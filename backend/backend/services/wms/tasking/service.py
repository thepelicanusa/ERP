from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from app.db.models.wms.tasking import Task, TaskStep, TaskException
from app.db.models.inventory_exec import Item, Location, InventoryBalance, HandlingUnit
from app.db.models.wms.counting import CountSubmission
from app.db.models.docs import InboundReceipt, InboundReceiptLine, OutboundOrder, OutboundOrderLine, CycleCountRequest, CycleCountLine
from services.wms.inventory_ops.service import apply_movement
from services.wms.inventory_ops.putaway_rules import suggest_putaway_location
from app.core.audit import AuditLog
from app.events.outbox import OutboxEvent

def create_receiving_and_putaway_tasks(db: Session, receipt_id: str, *, actor: str, staging_location_code: str = "STAGE"):
    receipt = db.query(InboundReceipt).filter(InboundReceipt.id == receipt_id).first()
    if not receipt:
        raise ValueError("Receipt not found")
    lines = db.query(InboundReceiptLine).filter(InboundReceiptLine.receipt_id == receipt_id).all()
    staging = db.query(Location).filter(Location.code == staging_location_code).first()
    if not staging:
        raise ValueError(f"Staging location '{staging_location_code}' not found")

    tasks: list[Task] = []
    for ln in lines:
        item = ln.item
        # RECEIVE task
        t_recv = Task(type="RECEIVE", status="READY", source_type="RECEIPT", source_id=receipt_id, context={
            "item_id": item.id,
            "expected_qty": float(ln.expected_qty),
            "staging_location_code": staging.code,
            "unit_cost": float(getattr(ln, "unit_cost", 0) or 0),
        })
        db.add(t_recv)
        db.flush()
        steps = [
            TaskStep(task_id=t_recv.id, seq=10, kind="SCAN_ITEM", prompt=f"Scan item SKU for receipt {receipt.ref}", expected={"sku": item.sku}),
            TaskStep(task_id=t_recv.id, seq=20, kind="ENTER_QTY", prompt="Enter received quantity", expected={"max": float(ln.expected_qty)}),
            TaskStep(task_id=t_recv.id, seq=30, kind="SCAN_LOCATION", prompt="Scan staging location", expected={"location_code": staging.code}),
        ]
        for s in steps:
            db.add(s)

        # PUTAWAY task (created READY; will move from staging to target bin)
        t_put = Task(type="PUTAWAY", status="READY", source_type="RECEIPT", source_id=receipt_id, context={
            "item_id": item.id,
            "qty": float(ln.expected_qty),
            "from_location_code": staging.code,
            "to_location_code": suggest_putaway_location(db, item=item, qty=float(ln.expected_qty)).code,  # rule engine
        })
        db.add(t_put)
        db.flush()
        steps2 = [
            TaskStep(task_id=t_put.id, seq=10, kind="SCAN_LOCATION", prompt="Scan FROM location", expected={"location_code": staging.code}),
            TaskStep(task_id=t_put.id, seq=20, kind="SCAN_LOCATION", prompt="Scan TO location", expected={"location_code": t_put.context["to_location_code"]}),
            TaskStep(task_id=t_put.id, seq=30, kind="CONFIRM", prompt="Confirm putaway", expected={}),
        ]
        for s in steps2:
            db.add(s)

        tasks.extend([t_recv, t_put])

    receipt.status = "RELEASED"
    db.add(AuditLog(actor=actor, action="RELEASE_RECEIPT", entity_type="InboundReceipt", entity_id=receipt.id, reason=None, data={"ref": receipt.ref}))
    db.add(OutboxEvent(topic="TasksCreated", payload={"source_type": "RECEIPT", "source_id": receipt.id, "task_count": len(tasks)}))
    db.commit()
    return tasks


def _best_pick_location_code(db: Session, item_id: str) -> str:
    from app.db.models.inventory_exec import InventoryBalance, Location
    # choose BIN with highest available qty
    rows = (db.query(InventoryBalance)
            .join(Location, Location.id == InventoryBalance.location_id)
            .filter(InventoryBalance.item_id == item_id, InventoryBalance.state == "AVAILABLE", Location.type == "BIN")
            .all())
    if not rows:
        return "BIN-A1"
    best = max(rows, key=lambda r: float(r.qty))
    return best.location.code


def create_pick_pack_tasks(db: Session, order_id: str, *, actor: str):
    order = db.query(OutboundOrder).filter(OutboundOrder.id == order_id).first()
    if not order:
        raise ValueError("Order not found")

    # Ensure allocations exist; if not, create best-effort picks from AVAILABLE
    from app.db.models.wms.allocation import Allocation
    allocs = db.query(Allocation).filter(Allocation.order_id == order_id).all()
    if not allocs:
        # fallback: create one pick per order line from best bin
        lines = db.query(OutboundOrderLine).filter(OutboundOrderLine.order_id == order_id).all()
        allocs = []
        for ln in lines:
            loc_code = _best_pick_location_code(db, ln.item_id)
            loc_obj = db.query(Location).filter(Location.code == loc_code).first()
            if loc_obj:
                a = Allocation(order_id=order_id, order_line_id=ln.id, item_id=ln.item_id, location_id=loc_obj.id, qty=float(ln.qty))
                db.add(a); db.flush()
                allocs.append(a)
        db.commit()

    tasks: list[Task] = []
    for a in allocs:
        item = db.query(Item).filter(Item.id == a.item_id).first()
        from_loc = db.query(Location).filter(Location.id == a.location_id).first()
        if not item or not from_loc:
            continue
        t_pick = Task(type="PICK", status="READY", source_type="ORDER", source_id=order_id, context={
            "order_id": order_id,
            "order_line_id": a.order_line_id,
            "allocation_id": a.id,
            "item_id": item.id,
            "qty": float(a.qty),
            "from_location_code": from_loc.code,
            "to_location_code": "PACK",
            "hu_id": a.handling_unit_id,
        })
        db.add(t_pick); db.flush()
        for s in [
            TaskStep(task_id=t_pick.id, seq=5, kind="SCAN_LPN", prompt="Scan LPN (if applicable)", expected={"lpn": ("*" if not a.handling_unit_id else "__ALLOCATED__")}),
            TaskStep(task_id=t_pick.id, seq=10, kind="SCAN_LOCATION", prompt="Scan pick location", expected={"location_code": from_loc.code}),
            TaskStep(task_id=t_pick.id, seq=20, kind="SCAN_ITEM", prompt="Scan item SKU", expected={"sku": item.sku}),
            TaskStep(task_id=t_pick.id, seq=30, kind="ENTER_QTY", prompt="Enter picked qty", expected={"max": float(a.qty)}),
        ]:
            db.add(s)
        tasks.append(t_pick)

    # One PACK task per order
    t_pack = Task(type="PACK", status="READY", source_type="ORDER", source_id=order_id, context={"order_id": order_id})
    db.add(t_pack); db.flush()
    for s in [
        TaskStep(task_id=t_pack.id, seq=10, kind="CONFIRM", prompt="Confirm all picks are packed", expected={}),
        TaskStep(task_id=t_pack.id, seq=20, kind="SCAN_LPN", prompt="Scan LPN(s) being packed (repeat scan)", expected={"lpn": "*"}),
    ]:
        db.add(s)
    tasks.append(t_pack)

    # One SHIP task per order
    t_ship = Task(type="SHIP", status="READY", source_type="ORDER", source_id=order_id, context={"order_id": order_id})
    db.add(t_ship); db.flush()
    for s in [
        TaskStep(task_id=t_ship.id, seq=10, kind="SCAN_LPN", prompt="Scan LPN(s) to ship (repeat scan)", expected={"lpn": "*"}),
        TaskStep(task_id=t_ship.id, seq=20, kind="CONFIRM", prompt="Confirm shipment", expected={}),
    ]:
        db.add(s)
    tasks.append(t_ship)

    db.commit()
    return tasks



def create_cycle_count_tasks(db: Session, request_id: str, *, actor: str):
    req = db.query(CycleCountRequest).filter(CycleCountRequest.id == request_id).first()
    if not req:
        raise ValueError("Count request not found")
    lines = db.query(CycleCountLine).filter(CycleCountLine.request_id == request_id).all()

    tasks: list[Task] = []
    for ln in lines:
        loc = ln.location
        t = Task(type="COUNT", status="READY", source_type="COUNT", source_id=request_id, context={"location_code": loc.code, "mode": "blind"})
        db.add(t); db.flush()
        for s in [
            TaskStep(task_id=t.id, seq=10, kind="SCAN_LOCATION", prompt="Scan location to count", expected={"location_code": loc.code}),
            TaskStep(task_id=t.id, seq=20, kind="SCAN_ITEM", prompt="Scan item SKU", expected={}),
            TaskStep(task_id=t.id, seq=30, kind="ENTER_QTY", prompt="Enter counted quantity", expected={}),
            TaskStep(task_id=t.id, seq=40, kind="CONFIRM", prompt="Confirm count submission", expected={}),
        ]:
            db.add(s)
        tasks.append(t)

    req.status = "RELEASED"
    db.add(AuditLog(actor=actor, action="RELEASE_COUNT", entity_type="CycleCountRequest", entity_id=req.id, reason=None, data={"ref": req.ref}))
    db.commit()
    return tasks

def get_my_tasks(db: Session, *, assignee: str):
    return (db.query(Task)
            .filter((Task.assignee == assignee) | (Task.assignee.is_(None)))
            .order_by(Task.priority.asc(), Task.created_at.asc())
            .all())

def get_task_with_steps(db: Session, task_id: str):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None, []
    steps = (db.query(TaskStep).filter(TaskStep.task_id == task_id).order_by(TaskStep.seq.asc()).all())
    return task, steps

def complete_step(db: Session, *, task_id: str, step_id: str, value: str | None, actor: str, reason: str | None = None):
    task = db.query(Task).filter(Task.id == task_id).first()
    step = db.query(TaskStep).filter(TaskStep.id == step_id, TaskStep.task_id == task_id).first()
    if not task or not step:
        raise ValueError("Task/step not found")
    if step.status == "DONE":
        return task, step

    # validate expected (lightweight v1)
    exp = step.expected or {}
    if step.kind == "SCAN_LOCATION" and exp.get("location_code") and value != exp["location_code"]:
        _raise_exception(db, task_id, "WRONG_LOCATION", f"Expected {exp['location_code']} got {value}", actor)
        task.status = "EXCEPTION"
        db.commit()
        return task, step
    if step.kind == "SCAN_ITEM" and exp.get("sku") and value != exp["sku"]:
        _raise_exception(db, task_id, "WRONG_ITEM", f"Expected {exp['sku']} got {value}", actor)
        task.status = "EXCEPTION"
        db.commit()
        return task, step

    step.status = "DONE"
    step.captured = {"value": value}
    task.status = "IN_PROGRESS"
    db.add(AuditLog(actor=actor, action="COMPLETE_TASK_STEP", entity_type="TaskStep", entity_id=step.id, reason=reason, data={"task_id": task.id, "kind": step.kind, "value": value}))
    db.commit()

    # if all steps done -> complete task + apply inventory movements where relevant
    steps = db.query(TaskStep).filter(TaskStep.task_id == task_id).all()
    if all(s.status == "DONE" for s in steps):
        _finalize_task(db, task, steps, actor=actor, reason=reason)
    return task, step

def _raise_exception(db: Session, task_id: str, code: str, message: str, actor: str):
    db.add(TaskException(task_id=task_id, code=code, message=message, data={"actor": actor}))
    db.add(OutboxEvent(topic="TaskExceptionRaised", payload={"task_id": task_id, "code": code, "message": message, "actor": actor}))

def _finalize_task(db: Session, task: Task, steps: list[TaskStep], *, actor: str, reason: str | None):
    # Apply inventory movements based on task type
    ctx = task.context or {}

    def loc(code: str) -> Location:
        l = db.query(Location).filter(Location.code == code).first()
        if not l:
            raise ValueError(f"Location {code} not found")
        return l

    if task.type == "RECEIVE":
        item = db.query(Item).filter(Item.id == ctx["item_id"]).first()
        qty = _get_qty_from_steps(steps) or float(ctx.get("expected_qty", 0))
        to_loc = loc(ctx["staging_location_code"])
        apply_movement(db, correlation_id=f"task:{task.id}", item=item, qty=qty, from_location=None, to_location=to_loc, actor=actor, reason=reason, meta={"task_type": "RECEIVE", "unit_cost": float(ctx.get("unit_cost", 0) or 0)})
    elif task.type == "PUTAWAY":
        item = db.query(Item).filter(Item.id == ctx["item_id"]).first()
        qty = float(ctx.get("qty", 0))
        from_loc = loc(ctx["from_location_code"])
        to_loc = loc(ctx["to_location_code"])
        apply_movement(db, correlation_id=f"task:{task.id}", item=item, qty=qty, from_location=from_loc, to_location=to_loc, actor=actor, reason=reason, meta={"task_type": "PUTAWAY"})
    
    elif task.type == "WAVE_PICK":
        # Multi-order picking using allocations (consumes RESERVED and moves to PACK).
        plan = (ctx.get("plan") or {})
        stops = plan.get("stops") or []
        pack_loc = db.query(Location).filter(Location.code == "PACK").first()
        if not pack_loc:
            pack_loc = db.query(Location).filter(Location.type == "STAGE").first()
    
        picked_lines = []
        for stop in stops:
            loc_code = stop.get("location_code")
            from_loc = loc(loc_code)
            for ln in stop.get("lines", []):
                sku = ln.get("sku")
                qty = float(ln.get("qty", 0))
                tote_code = ln.get("tote_code")
                order_id = ln.get("order_id")
                if not sku or qty <= 0:
                    continue
                item_obj = db.query(Item).filter(Item.sku == sku).first()
                if not item_obj:
                    continue
                # consume RESERVED then move physical
                _consume_reserved(db, item_id=item_obj.id, location_id=from_loc.id, qty=qty)
                apply_movement(db, correlation_id=f"wavepick:{task.id}:{order_id}", item=item_obj, qty=qty, from_location=from_loc, to_location=pack_loc, actor=actor, reason=reason)
                picked_lines.append({"order_id": order_id, "sku": sku, "qty": qty, "from": from_loc.code, "to": pack_loc.code if pack_loc else None, "tote_code": tote_code})
    
        db.add(OutboxEvent(topic="WavePickCompleted", payload={"task_id": task.id, "wave_id": ctx.get("wave_id"), "cart": plan.get("cart"), "picked": picked_lines}))
    
    elif task.type == "PICK":
        item = db.query(Item).filter(Item.id == ctx["item_id"]).first()
        expected = float(ctx.get("qty", 0))
        picked = _get_qty_from_steps(steps) or expected
        from_loc = loc(ctx["from_location_code"])
        to_loc = loc(ctx["to_location_code"])

        # Consume RESERVED at pick location, move to PACK as AVAILABLE
        hu_id = ctx.get("hu_id")
        if picked > 0:
            apply_movement(db, correlation_id=f"task:{task.id}:resv_out", item=item, qty=picked, from_location=from_loc, to_location=None,
                          state="RESERVED", actor=actor, reason=reason, handling_unit_id=hu_id, meta={"task_type": "PICK"})
            apply_movement(db, correlation_id=f"task:{task.id}:pack_in", item=item, qty=picked, from_location=None, to_location=to_loc,
                          state="AVAILABLE", actor=actor, reason=reason, handling_unit_id=hu_id, meta={"task_type": "PICK"})

        # Short pick: release remaining reservation back to AVAILABLE and create exception
        if picked + 1e-9 < expected:
            remaining = expected - picked
            from services.wms.inventory_ops.reservation import release
            release(db, correlation_id=f"short:{task.id}", item=item, qty=remaining, location=from_loc, handling_unit_id=hu_id, actor=actor, reason="short-pick release")
            db.add(TaskException(task_id=task.id, kind="SHORT_PICK", status="OPEN", data={
                "order_id": ctx.get("order_id"),
                "order_line_id": ctx.get("order_line_id"),
                "allocation_id": ctx.get("allocation_id"),
                "item_id": ctx.get("item_id"),
                "from_location_code": ctx.get("from_location_code"),
                "expected_qty": expected,
                "picked_qty": picked,
                "remaining_qty": remaining,
            }))
            db.add(OutboxEvent(topic="ShortPickRecorded", payload={"task_id": task.id, "order_id": ctx.get("order_id"), "remaining_qty": remaining}))


    elif task.type == "PACK":
        from app.db.models.docs import Shipment, ShipmentHandlingUnit
        from app.db.models.inventory_exec import HandlingUnit

        order_id = ctx.get("order_id") or task.source_id
        shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
        if not shipment:
            shipment = Shipment(order_id=order_id, status="CREATED")
            db.add(shipment); db.flush()

        # optional: capture one LPN for v1
        lpn = None
        for s in steps:
            if s.kind == "SCAN_LPN" and s.captured and s.captured.get("value"):
                lpn = s.captured.get("value")
        if lpn and lpn != "*":
            hu = db.query(HandlingUnit).filter(HandlingUnit.lpn == lpn).first()
            if hu:
                hu.status = "CLOSED"
                link = ShipmentHandlingUnit(shipment_id=shipment.id, handling_unit_id=hu.id)
                db.add(link)

        shipment.status = "PACKED"
        db.add(OutboxEvent(topic="ShipmentPacked", payload={"shipment_id": shipment.id, "order_id": order_id, "lpn": lpn}))


    elif task.type == "SHIP":
        from app.db.models.docs import Shipment, ShipmentHandlingUnit
        from app.db.models.inventory_exec import HandlingUnit

        order_id = ctx.get("order_id") or task.source_id
        shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
        if not shipment:
            shipment = Shipment(order_id=order_id, status="CREATED")
            db.add(shipment); db.flush()

        lpn = None
        for s in steps:
            if s.kind == "SCAN_LPN" and s.captured and s.captured.get("value"):
                lpn = s.captured.get("value")
        if lpn and lpn != "*":
            hu = db.query(HandlingUnit).filter(HandlingUnit.lpn == lpn).first()
            if hu:
                hu.status = "SHIPPED"
                # ensure association
                exists = db.query(ShipmentHandlingUnit).filter(ShipmentHandlingUnit.shipment_id == shipment.id, ShipmentHandlingUnit.handling_unit_id == hu.id).first()
                if not exists:
                    db.add(ShipmentHandlingUnit(shipment_id=shipment.id, handling_unit_id=hu.id))

        shipment.status = "SHIPPED"
        db.add(OutboxEvent(topic="ShipmentShipped", payload={"shipment_id": shipment.id, "order_id": order_id, "lpn": lpn}))

    elif task.type == "COUNT":
        # Record count submission + variance vs current balance.
        loc_obj = loc(ctx["location_code"])
        # In this starter, count flow captures one item+qty per task (can be expanded to multi-line).
        sku = None
        counted_qty = None
        for s in steps:
            if s.kind == "SCAN_ITEM":
                sku = s.captured.get("value")
            if s.kind == "ENTER_QTY":
                try:
                    counted_qty = float(s.captured.get("value"))
                except Exception:
                    counted_qty = 0.0
        if not sku:
            sku = "__UNKNOWN__"
        item_obj = db.query(Item).filter(Item.sku == sku).first()
        if not item_obj:
            # Unknown item -> exception
            db.add(OutboxEvent(topic="CountSubmitted", payload={"task_id": task.id, "location_code": ctx["location_code"], "unknown_sku": sku}))
        else:
            bal = (db.query(InventoryBalance)
                   .filter(InventoryBalance.item_id == item_obj.id, InventoryBalance.location_id == loc_obj.id, InventoryBalance.state == "AVAILABLE")
                   .first())
            expected = float(bal.qty) if bal else 0.0
            variance = (counted_qty or 0.0) - expected
            sub = CountSubmission(
                task_id=task.id,
                location_id=loc_obj.id,
                item_id=item_obj.id,
                counted_qty=counted_qty or 0.0,
                expected_qty=expected,
                variance_qty=variance,
                status="PENDING_REVIEW" if abs(variance) > 0.000001 else "APPROVED",
                reviewed_by=actor if abs(variance) <= 0.000001 else None,
                reviewed_at=datetime.utcnow() if abs(variance) <= 0.000001 else None,
                reason=reason,
                meta={"mode": ctx.get("mode","blind")}
            )
            db.add(sub)
            db.add(OutboxEvent(topic="CountVarianceDetected" if abs(variance) > 0.000001 else "CountMatched",
                               payload={"task_id": task.id, "location_code": ctx["location_code"], "sku": sku, "counted": counted_qty or 0.0, "expected": expected, "variance": variance}))


    task.status = "DONE"
    db.add(AuditLog(actor=actor, action="COMPLETE_TASK", entity_type="Task", entity_id=task.id, reason=reason, data={"type": task.type}))
    db.add(OutboxEvent(topic="TaskCompleted", payload={"task_id": task.id, "type": task.type, "actor": actor}))
    db.commit()

def _get_qty_from_steps(steps: list[TaskStep]) -> float | None:
    for s in steps:
        if s.kind == "ENTER_QTY":
            v = s.captured.get("value")
            try:
                return float(v) if v is not None and v != "" else None
            except Exception:
                return None
    return None
