from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models.inventory_exec import InventoryBalance, Location, Item
from services.wms.inventory_ops.service import apply_movement

def reserve_from_balance(db: Session, *, correlation_id: str, item_id: str, location_id: str, qty: float, actor: str, reason: str | None):
    # Represent reservation as internal movement AVAILABLE -> RESERVED within same location.
    item = db.query(Item).filter(Item.id == item_id).first()
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not item or not loc:
        raise ValueError("Bad item or location")

    # subtract from AVAILABLE (to nil location but state change handled by apply_movement? In this starter we emulate by moving out then in with state)
    # We do it by manual balance update for states while still writing a txn via apply_movement with meta.
    # v1: use apply_movement to create txn, then adjust balances by state directly.
    # Decrement AVAILABLE
    bal_av = (db.query(InventoryBalance)
              .filter(InventoryBalance.item_id == item_id, InventoryBalance.location_id == location_id, InventoryBalance.state == "AVAILABLE")
              .with_for_update()
              .first())
    if not bal_av or float(bal_av.qty) < qty - 1e-9:
        raise ValueError("Insufficient available qty to reserve")
    bal_av.qty = float(bal_av.qty) - qty

    # Increment RESERVED
    bal_res = (db.query(InventoryBalance)
               .filter(InventoryBalance.item_id == item_id, InventoryBalance.location_id == location_id, InventoryBalance.state == "RESERVED")
               .with_for_update()
               .first())
    if not bal_res:
        bal_res = InventoryBalance(item_id=item_id, location_id=location_id, state="RESERVED", qty=0)
        db.add(bal_res)
    bal_res.qty = float(bal_res.qty) + qty

    # Write a txn marker
    apply_movement(db, correlation_id=correlation_id, item=item, qty=qty, from_location=loc, to_location=loc, actor=actor, reason=reason)

def release_reservation(db: Session, *, correlation_id: str, item_id: str, location_id: str, qty: float, actor: str, reason: str | None):
    item = db.query(Item).filter(Item.id == item_id).first()
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not item or not loc:
        raise ValueError("Bad item or location")

    bal_res = (db.query(InventoryBalance)
               .filter(InventoryBalance.item_id == item_id, InventoryBalance.location_id == location_id, InventoryBalance.state == "RESERVED")
               .with_for_update()
               .first())
    if not bal_res or float(bal_res.qty) < qty - 1e-9:
        # best effort: nothing to release
        return

    bal_res.qty = float(bal_res.qty) - qty

    bal_av = (db.query(InventoryBalance)
              .filter(InventoryBalance.item_id == item_id, InventoryBalance.location_id == location_id, InventoryBalance.state == "AVAILABLE")
              .with_for_update()
              .first())
    if not bal_av:
        bal_av = InventoryBalance(item_id=item_id, location_id=location_id, state="AVAILABLE", qty=0)
        db.add(bal_av)
    bal_av.qty = float(bal_av.qty) + qty

    apply_movement(db, correlation_id=correlation_id, item=item, qty=qty, from_location=loc, to_location=loc, actor=actor, reason=reason)
