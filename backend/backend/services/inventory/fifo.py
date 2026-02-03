from __future__ import annotations
from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.tenant import get_tenant_id
from app.db.models.inventory_exec import InventoryBalance, InventoryTxn

def fifo_issue(
    db: Session,
    *,
    correlation_id: str,
    item_id: str,
    location_id: str | None,
    qty: Decimal,
    actor: str,
    reason: str,
    lot_id: str | None = None,
    state: str = "AVAILABLE",
    unit_cost: Decimal | None = None,
    meta: dict | None = None,
) -> list[InventoryTxn]:
    """Consume inventory balances FIFO (oldest first) and emit ISSUE_TO_WIP txns.
    Returns list of created txns. Updates balances in-place.
    """
    remaining = Decimal(qty)
    created: list[InventoryTxn] = []
    q = db.query(InventoryBalance).filter(
        InventoryBalance.item_id == item_id,
        InventoryBalance.state == state,
        InventoryBalance.qty > 0,
    )
    if location_id:
        q = q.filter(InventoryBalance.location_id == location_id)
    if lot_id:
        q = q.filter(InventoryBalance.lot_id == lot_id)

    # FIFO by created_at (or id as tie-breaker)
    balances = q.order_by(InventoryBalance.created_at.asc(), InventoryBalance.id.asc()).all()

    for b in balances:
        if remaining <= 0:
            break
        take = b.qty if b.qty <= remaining else remaining
        b.qty = b.qty - take
        remaining -= take

        tx = InventoryTxn(
            correlation_id=correlation_id,
            txn_type="ISSUE_TO_WIP",
            item_id=item_id,
            from_location_id=b.location_id,
            to_location_id=None,
            lot_id=b.lot_id,
            handling_unit_id=b.handling_unit_id,
            state=b.state,
            qty=take,
            unit_cost=unit_cost,
            ext_cost=(unit_cost * take) if unit_cost is not None else None,
            uom="EA",
            actor=actor,
            reason=reason,
            meta={**(meta or {}), "tenant_id": get_tenant_id()},
        )
        db.add(tx)
        created.append(tx)

    if remaining > 0:
        raise ValueError(f"Insufficient inventory for FIFO issue: short {remaining}")

    db.commit()
    for tx in created:
        db.refresh(tx)
    return created
