from __future__ import annotations
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.models.planning import Wave, WaveOrder
from app.db.models.docs import OutboundOrder
from services.wms.inventory_ops.allocation_service import allocate_order
from services.wms.tasking.service import create_pick_pack_tasks
from services.wms.tasking.wave_pick import create_wave_pick_task
from app.events.outbox import OutboxEvent

def create_wave(db: Session, *, code: str, created_by: str | None, order_ids: list[str]) -> Wave:
    w = Wave(code=code, status="PLANNED", created_by=created_by)
    db.add(w); db.flush()
    for oid in order_ids:
        db.add(WaveOrder(wave_id=w.id, order_id=oid, status="IN_WAVE"))
    db.add(OutboxEvent(topic="WaveCreated", payload={"wave_id": w.id, "code": code, "orders": order_ids}))
    db.commit()
    return w

def release_wave(db: Session, *, wave_id: str, actor: str):
    wv = db.query(Wave).filter(Wave.id == wave_id).first()
    if not wv:
        raise ValueError("Wave not found")
    if wv.status != "PLANNED":
        return wv

    orders = db.query(WaveOrder).filter(WaveOrder.wave_id == wave_id).all()
    for wo in orders:
        # Allocate and reserve per order
        allocate_order(db, wo.order_id, create_backorders=True)
        # Create PACK task per order (pick happens at wave level)
        create_pick_pack_tasks(db, wo.order_id, pick_only=False)
        wo.status = "PICKING"

    # Create one multi-order WAVE_PICK task
    create_wave_pick_task(db, wave_id)

    wv.status = "RELEASED"
    wv.released_at = datetime.utcnow()
    db.add(OutboxEvent(topic="WaveReleased", payload={"wave_id": wave_id}))
    db.commit()
    return wv
