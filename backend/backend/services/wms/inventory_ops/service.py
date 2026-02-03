from __future__ import annotations
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.db.models.inventory_exec import InventoryTxn, InventoryBalance, Item, Location, Lot
from app.events.outbox import OutboxEvent

def _dec(x) -> Decimal:
    return Decimal(str(x))



def _fifo_add_layer(db: Session, *, item_id: str, location_id: str | None, qty: float, unit_cost: float, correlation_id: str | None):
    if qty <= 0:
        return
    db.add(FifoLayer(item_id=item_id, location_id=location_id, qty_remaining=qty, unit_cost=unit_cost, correlation_id=correlation_id, meta={}))

def _fifo_consume(db: Session, *, item_id: str, location_id: str | None, qty: float) -> float:
    # returns extended cost consumed
    remaining = qty
    ext = 0.0
    q = (db.query(FifoLayer)
         .filter(FifoLayer.item_id == item_id)
         .order_by(FifoLayer.created_at.asc())
         .all())
    for layer in q:
        if remaining <= 1e-9:
            break
        take = min(float(layer.qty_remaining), remaining)
        if take <= 0:
            continue
        layer.qty_remaining = float(layer.qty_remaining) - take
        remaining -= take
        ext += take * float(layer.unit_cost)
    # if not enough layers, ext will be partial; caller can fallback
    return ext

def _get_or_create_item_cost(db: Session, item_id: str) -> ItemCost:
    ic = db.query(ItemCost).filter(ItemCost.item_id == item_id).first()
    if not ic:
        ic = ItemCost(item_id=item_id, method="AVG", currency="USD", avg_cost=0, std_cost=0, meta={})
        db.add(ic); db.flush()
    return ic

def _record_valuation(db: Session, *, item: Item, qty: float, direction: str, correlation_id: str | None, unit_cost: float, meta: dict | None = None):
    ext = qty * unit_cost
    db.add(ValuationTxn(item_id=item.id, qty=qty, unit_cost=unit_cost, extended_cost=ext, direction=direction, correlation_id=correlation_id, meta=meta or {}))

def apply_movement(
    db: Session,
    *,
    correlation_id: str,
    item: Item,
    qty: float,
    from_location: Location | None,
    to_location: Location | None,
    state: str = "AVAILABLE",
    lot: Lot | None = None,
    handling_unit_id: str | None = None,
    uom: str = "EA",
    actor: str,
    reason: str | None = None,
    meta: dict | None = None,
) -> InventoryTxn:
    # Idempotency: if we already have a txn with same correlation+item+from+to+lot+state+qty, return it
    existing = (db.query(InventoryTxn)
        .filter(
            InventoryTxn.correlation_id == correlation_id,
            InventoryTxn.item_id == item.id,
            InventoryTxn.from_location_id == (from_location.id if from_location else None),
            InventoryTxn.to_location_id == (to_location.id if to_location else None),
            InventoryTxn.lot_id == (lot.id if lot else None),
            InventoryTxn.handling_unit_id == handling_unit_id,
            InventoryTxn.state == state,
            InventoryTxn.qty == _dec(qty),
        )
        .first()
    )
    if existing:
        return existing

    txn = InventoryTxn(
        correlation_id=correlation_id,
        item_id=item.id,
        from_location_id=from_location.id if from_location else None,
        to_location_id=to_location.id if to_location else None,
        lot_id=lot.id if lot else None,
        handling_unit_id=handling_unit_id,
        state=state,
        qty=_dec(qty),
        uom=uom,
        actor=actor,
        reason=reason,
        meta=meta or {},
    )
    db.add(txn)

    # decrement from
    if from_location:
        _apply_balance(db, item_id=item.id, location_id=from_location.id, lot_id=lot.id if lot else None,
        handling_unit_id=handling_unit_id, state=state, delta=-_dec(qty))
    # increment to
    if to_location:
        _apply_balance(db, item_id=item.id, location_id=to_location.id, lot_id=lot.id if lot else None,
        handling_unit_id=handling_unit_id, state=state, delta=_dec(qty))

    
    # Costing / valuation + FIFO (starter)
    try:
        ic = _get_or_create_item_cost(db, item.id)
        avg = float(ic.avg_cost or 0)
        # Receipt into stock: from_location None -> to_location not None
        if to_location is not None and from_location is None:
            # Prefer explicit unit_cost passed via meta (e.g., PO receipt / MO receipt)
            unit_cost = float((meta or {}).get("unit_cost") or 0)
            if unit_cost <= 0:
                unit_cost = avg if avg > 0 else float(ic.std_cost or 0)
            # FIFO layer at the receipt cost
            _fifo_add_layer(db, item_id=item.id, location_id=to_location.id, qty=qty, unit_cost=unit_cost, correlation_id=correlation_id)
            # Update AVG cost (moving average, using pre-receipt qty estimate)
            old_qty = sum(float(b.qty) for b in db.query(InventoryBalance).filter(InventoryBalance.item_id == item.id).all())
            # balances already updated, so estimate old_qty by subtracting this receipt qty
            old_qty = max(old_qty - float(qty), 0.0)
            new_qty = old_qty + float(qty)
            if new_qty > 0:
                ic.avg_cost = (avg * old_qty + unit_cost * float(qty)) / new_qty
            _record_valuation(db, item=item, qty=float(qty), direction="IN", correlation_id=correlation_id, unit_cost=unit_cost, meta={"mode": "receipt"})
        # Issue out of stock: from_location not None -> to_location None
        elif from_location is not None and to_location is None:
            ext = _fifo_consume(db, item_id=item.id, location_id=from_location.id, qty=float(qty))
            unit_cost = (ext / float(qty)) if ext > 0 and float(qty) > 0 else avg
            _record_valuation(db, item=item, qty=float(qty), direction="OUT", correlation_id=correlation_id, unit_cost=unit_cost, meta={"mode": "issue", "fifo_ext_cost": ext})
        # Internal move: no valuation impact
    except Exception:
        pass

    db.add(OutboxEvent(topic="InventoryChanged", payload={
        "correlation_id": correlation_id,
        "item_id": item.id,
        "from_location_id": from_location.id if from_location else None,
        "to_location_id": to_location.id if to_location else None,
        "lot_id": lot.id if lot else None,
        "handling_unit_id": handling_unit_id,
        "state": state,
        "qty": float(qty),
        "uom": uom,
        "actor": actor,
        "reason": reason,
    }))
    db.commit()
    db.refresh(txn)
    return txn

def _apply_balance(db: Session, *, item_id: str, location_id: str, lot_id: str | None, handling_unit_id: str | None, state: str, delta: Decimal):
    bal = (db.query(InventoryBalance)
           .filter(
               InventoryBalance.item_id == item_id,
               InventoryBalance.location_id == location_id,
               InventoryBalance.lot_id == lot_id,
                InventoryBalance.handling_unit_id == handling_unit_id,
               InventoryBalance.state == state,
           ).first())
    if not bal:
        bal = InventoryBalance(item_id=item_id, location_id=location_id, lot_id=lot_id, state=state, qty=Decimal("0"))
        db.add(bal)
    bal.qty = _dec(bal.qty) + delta
