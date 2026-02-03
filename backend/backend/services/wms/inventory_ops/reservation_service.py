from sqlalchemy.orm import Session
from app.db.models.inventory_exec import InventoryBalance, Location, Item
from services.wms.inventory_ops.service import apply_movement
from app.events.outbox import OutboxEvent

def reserve_inventory(db: Session, *, order_id: str, item: Item, location: Location, qty: float, actor: str):
    # Move qty from AVAILABLE to RESERVED (same location)
    # Implemented as two movements for audit clarity
    apply_movement(
        db,
        correlation_id=f"reserve:{order_id}",
        item=item,
        qty=qty,
        from_location=location,
        to_location=None,
        actor=actor,
        reason="Reserve inventory",
    )
    apply_movement(
        db,
        correlation_id=f"reserve:{order_id}",
        item=item,
        qty=qty,
        from_location=None,
        to_location=location,
        actor=actor,
        reason="Reserve inventory",
    )
    # Patch balance state
    bal = (db.query(InventoryBalance)
           .filter(InventoryBalance.item_id == item.id,
                   InventoryBalance.location_id == location.id,
                   InventoryBalance.state == "AVAILABLE")
           .first())
    if bal:
        bal.state = "RESERVED"
    db.add(OutboxEvent(topic="InventoryReserved", payload={
        "order_id": order_id,
        "item_id": item.id,
        "location_code": location.code,
        "qty": qty,
    }))
    db.commit()
