from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import asc
from app.db.models.planning import WaveOrder
from app.db.models.wms.allocation import Allocation
from app.db.models.inventory_exec import Location, Item

@dataclass(frozen=True)
class LocKey:
    zone: str
    aisle: int
    bay: int
    level: int
    pos: int
    code: str

def _to_int(x: str | None, default: int = 0) -> int:
    try:
        return int(x) if x is not None else default
    except Exception:
        return default

def parse_location(loc: Location) -> LocKey:
    # Uses Location.zone when present; otherwise tries to parse from code.
    code = loc.code or ""
    zone = (getattr(loc, "zone", None) or "") or _to_zone(code)
    aisle, bay, level, pos = _parse_code_dims(code)
    return LocKey(zone=zone or "Z0", aisle=aisle, bay=bay, level=level, pos=pos, code=code)

def _to_zone(code: str) -> str:
    # Examples supported:
    # Z1-A02-B03-L01-P05
    # Z1-A02-03-01-05
    m = re.search(r"\bZ(\d+)\b", code, re.IGNORECASE)
    if m:
        return f"Z{_to_int(m.group(1), 0)}"
    # fallback: first token
    tok = code.split("-")[0].strip()
    return tok if tok else "Z0"

def _parse_code_dims(code: str):
    # We try multiple patterns to extract aisle/bay/level/pos.
    # If missing, default 0.
    aisle = bay = level = pos = 0
    # Aisle like A02 or AISLE-02
    m = re.search(r"(?:\bA(?:ISLE)?[- ]?)(\d+)", code, re.IGNORECASE)
    if m:
        aisle = _to_int(m.group(1), 0)
    # Bay/Bin like B03
    m = re.search(r"(?:\bB|\bBAY[- ]?)(\d+)", code, re.IGNORECASE)
    if m:
        bay = _to_int(m.group(1), 0)
    # Level like L01
    m = re.search(r"(?:\bL|\bLVL[- ]?)(\d+)", code, re.IGNORECASE)
    if m:
        level = _to_int(m.group(1), 0)
    # Position like P05
    m = re.search(r"(?:\bP|\bPOS[- ]?)(\d+)", code, re.IGNORECASE)
    if m:
        pos = _to_int(m.group(1), 0)

    # If still empty, attempt hyphen-separated numeric dims (Z?-A?-B?-L?-P?)
    parts = [p for p in re.split(r"[-_ ]+", code) if p]
    # crude: take last 4 numeric tokens as aisle,bay,level,pos if not found
    nums = []
    for p in parts:
        if p.isdigit():
            nums.append(int(p))
        elif re.match(r"^\d+$", p):
            nums.append(int(p))
    if nums:
        if aisle == 0 and len(nums) >= 1:
            aisle = nums[-4] if len(nums) >= 4 else nums[0]
        if bay == 0 and len(nums) >= 2:
            bay = nums[-3] if len(nums) >= 3 else nums[1]
        if level == 0 and len(nums) >= 3:
            level = nums[-2]
        if pos == 0 and len(nums) >= 4:
            pos = nums[-1]
    return aisle, bay, level, pos

def _distance(a: LocKey, b: LocKey) -> int:
    # Simple warehouse heuristic distance (no coordinates):
    # zone change is expensive; aisle change next; then bay/pos.
    dz = 10000 if a.zone != b.zone else 0
    return dz + abs(a.aisle - b.aisle) * 100 + abs(a.bay - b.bay) * 10 + abs(a.pos - b.pos)

def order_stops(stops: list[dict[str, Any]], keys: dict[str, LocKey]) -> list[dict[str, Any]]:
    if not stops:
        return stops
    remaining = stops[:]
    # start at the smallest zone/aisle
    remaining.sort(key=lambda s: (keys[s["location_id"]].zone, keys[s["location_id"]].aisle, keys[s["location_id"]].bay, keys[s["location_id"]].pos))
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        lk = keys[last["location_id"]]
        # nearest neighbor selection
        next_idx = min(range(len(remaining)), key=lambda i: _distance(lk, keys[remaining[i]["location_id"]]))
        ordered.append(remaining.pop(next_idx))
    return ordered

def assign_totes(order_ids: list[str], *, max_orders_per_tote: int = 4) -> dict[str, str]:
    # Assign each order to a tote. Multiple totes can be carried on a cart.
    tote_map: dict[str, str] = {}
    tote_count = max(1, (len(order_ids) + max_orders_per_tote - 1) // max_orders_per_tote)
    totes = [f"TOTE-{i+1:02d}" for i in range(tote_count)]
    for idx, oid in enumerate(order_ids):
        tote_map[oid] = totes[idx // max_orders_per_tote]
    return tote_map

def build_wave_pick_plan(db: Session, wave_id: str) -> dict:
    order_ids = [wo.order_id for wo in db.query(WaveOrder).filter(WaveOrder.wave_id == wave_id).all()]
    if not order_ids:
        return {"wave_id": wave_id, "stops": [], "totes": []}

    allocs = db.query(Allocation).filter(Allocation.order_id.in_(order_ids)).all()

    by_loc: dict[str, dict] = {}
    for a in allocs:
        loc = by_loc.setdefault(a.location_id, {"location_id": a.location_id, "lines": []})
        loc["lines"].append({"order_id": a.order_id, "order_line_id": a.order_line_id, "item_id": a.item_id, "qty": float(a.qty)})

    loc_rows = (db.query(Location)
                .filter(Location.id.in_(list(by_loc.keys())))
                .order_by(asc(Location.code))
                .all())
    id_to_loc = {l.id: l for l in loc_rows}
    keys = {lid: parse_location(id_to_loc[lid]) for lid in by_loc.keys() if lid in id_to_loc}

    tote_map = assign_totes(order_ids, max_orders_per_tote=4)
    totes = sorted(set(tote_map.values()))

    # Decorate stops
    stops = []
    for loc_id, stop in by_loc.items():
        loc = id_to_loc.get(loc_id)
        k = keys.get(loc_id, LocKey("Z0", 0, 0, 0, 0, (loc.code if loc else "")))
        stop["location_code"] = (loc.code if loc else None)
        stop["zone"] = k.zone
        stop["aisle"] = k.aisle
        stop["bay"] = k.bay
        stop["level"] = k.level
        stop["pos"] = k.pos
        # add sku + tote
        item_ids = [ln["item_id"] for ln in stop["lines"]]
        items = db.query(Item).filter(Item.id.in_(item_ids)).all()
        sku = {i.id: i.sku for i in items}
        for ln in stop["lines"]:
            ln["sku"] = sku.get(ln["item_id"])
            ln["tote_code"] = tote_map.get(ln["order_id"])
        stop["lines"].sort(key=lambda ln: (ln.get("tote_code") or "", ln.get("sku") or "", ln["order_id"]))
        stops.append(stop)

    # Path heuristics: zone/aisle clustering + nearest-neighbor between stops
    ordered_stops = order_stops(stops, keys)

    # Cart assignment: v1 assume one cart per wave, carrying the computed totes
    cart = {"cart_code": f"CART-{wave_id[:6]}", "totes": totes}

    return {
        "wave_id": wave_id,
        "order_ids": order_ids,
        "cart": cart,
        "totes": totes,
        "tote_map": tote_map,
        "stops": ordered_stops,
        "heuristics": {
            "cluster": "zone/aisle + nearest-neighbor",
            "distance_metric": "zone heavy, aisle medium, bay/pos light",
            "max_orders_per_tote": 4,
        },
    }
