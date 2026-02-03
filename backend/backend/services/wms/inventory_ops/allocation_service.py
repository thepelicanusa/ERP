from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from app.db.models.docs import OutboundOrder, OutboundOrderLine
from app.db.models.inventory_exec import InventoryBalance, Location, Item
from app.db.models.wms.allocation import Allocation
from app.db.models.planning import Backorder
from services.wms.inventory_ops.reservation import reserve_from_balance, release_reservation
from app.events.outbox import OutboxEvent

def allocate_order(db: Session, order_id: str, *, create_backorders: bool = True) -> dict:
    order = db.query(OutboundOrder).filter(OutboundOrder.id == order_id).first()
    if not order:
        raise ValueError("Order not found")

    lines = db.query(OutboundOrderLine).filter(OutboundOrderLine.order_id == order_id).all()

    # Clear existing allocations and release any outstanding reservations for this order (idempotent behavior).
    existing = db.query(Allocation).filter(Allocation.order_id == order_id).all()
    for a in existing:
        # release reservation back to AVAILABLE (best effort)
        release_reservation(db, correlation_id=f"dealloc:{order_id}", item_id=a.item_id, location_id=a.location_id, qty=float(a.qty), actor="system", reason="reallocate")
    db.query(Allocation).filter(Allocation.order_id == order_id).delete()
    if create_backorders:
        db.query(Backorder).filter(Backorder.order_id == order_id, Backorder.status == "OPEN").delete()

    allocations = 0
    short = []

    for ln in lines:
        item = db.query(Item).filter(Item.id == ln.item_id).first()
        need = float(ln.qty)

        # Lock balances for this item in BIN locations to enforce hard reservation.
        rows = (db.query(InventoryBalance)
                .join(Location, Location.id == InventoryBalance.location_id)
                .filter(InventoryBalance.item_id == ln.item_id,
                        InventoryBalance.state == "AVAILABLE",
                        Location.type == "BIN")
                .order_by(desc(InventoryBalance.qty))
                .with_for_update()
                .all())

        for b in rows:
            if need <= 0:
                break
            avail = float(b.qty)
            if avail <= 0:
                continue
            take = min(avail, need)

            # Reserve: AVAILABLE -> RESERVED (enforced by txn + balance updates)
            reserve_from_balance(db, correlation_id=f"alloc:{order_id}:{ln.id}", item_id=ln.item_id, location_id=b.location_id, qty=take,
                                 actor="system", reason="allocation")

            a = Allocation(order_id=order_id, order_line_id=ln.id, item_id=ln.item_id, location_id=b.location_id, qty=take)
            db.add(a)
            allocations += 1
            need -= take

        if need > 0:
            short.append({"order_line_id": ln.id, "item_id": ln.item_id, "short_qty": need, "sku": item.sku if item else None})
            if create_backorders:
                bo = Backorder(order_id=order_id, order_line_id=ln.id, item_id=ln.item_id, qty=need, status="OPEN", meta={"created_at": datetime.utcnow().isoformat()})
                db.add(bo)

    db.add(OutboxEvent(topic="OrderAllocated", payload={"order_id": order_id, "short": short}))
    db.commit()
    return {"order_id": order_id, "allocations": allocations, "short": short}
