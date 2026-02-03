from __future__ import annotations
from sqlalchemy.orm import Session
from collections import defaultdict
from app.db.models.planning import WaveOrder
from app.db.models.inventory_exec import InventoryBalance, Location

def optimize_wave(db: Session, wave_id: str) -> dict:
    # Simple heuristic:
    # - group picks by location.zone
    # - order zones alphabetically
    # - within zone, highest qty first
    orders = db.query(WaveOrder).filter(WaveOrder.wave_id == wave_id).all()
    zone_map = defaultdict(list)

    for wo in orders:
        balances = (db.query(InventoryBalance)
                    .join(Location, Location.id == InventoryBalance.location_id)
                    .filter(InventoryBalance.state == "RESERVED")
                    .all())
        for b in balances:
            zone_map[b.location.zone or "ZZZ"].append({
                "order_id": wo.order_id,
                "location_code": b.location.code,
                "zone": b.location.zone,
                "qty": float(b.qty)
            })

    sequence = []
    for zone in sorted(zone_map.keys()):
        rows = sorted(zone_map[zone], key=lambda r: -r["qty"])
        sequence.extend(rows)

    return {
        "wave_id": wave_id,
        "sequence": sequence
    }
