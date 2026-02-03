from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models.inventory_exec import Item, Location, InventoryBalance

# v1 rule engine:
# - prefer bins in item's preferred zone if provided
# - otherwise any BIN location
# - basic capacity: if capacity_units set, prefer locations where total qty < capacity_units (soft)
def suggest_putaway_location(db: Session, *, item: Item, qty: float) -> Location:
    # preferred zone can be stored in item.description or later a proper field; use meta in future
    pref_zone = None
    # try parse "zone:XYZ" from description
    if item.description and "zone:" in item.description:
        try:
            pref_zone = item.description.split("zone:")[1].split()[0].strip()
        except Exception:
            pref_zone = None

    q = db.query(Location).filter(Location.type == "BIN")
    if pref_zone:
        q = q.filter(Location.zone == pref_zone)
    locs = q.order_by(Location.code.asc()).all()
    if not locs and pref_zone:
        locs = db.query(Location).filter(Location.type == "BIN").order_by(Location.code.asc()).all()
    if not locs:
        raise ValueError("No BIN locations exist")

    # capacity preference
    best = None
    best_ratio = None
    for l in locs:
        if l.capacity_units is None:
            return l
        total = db.query(InventoryBalance).filter(InventoryBalance.location_id == l.id).all()
        tot_qty = sum(float(b.qty) for b in total)
        ratio = (tot_qty + qty) / max(l.capacity_units, 1)
        if best is None or ratio < best_ratio:
            best = l
            best_ratio = ratio
    return best or locs[0]
