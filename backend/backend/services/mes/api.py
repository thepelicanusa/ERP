from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
import uuid

from app.db.session import get_db
from app.core.security import get_principal
from services.admin.module_guard import require_module_enabled
from app.core.tenant import get_tenant_id

from app.db.models.mes_exec import WorkCenter, Routing, ProductionOrder, ProductionMaterial
from app.db.models.inventory import InventoryItem
from app.db.models.inventory_exec import InventoryTxn, WIPBalance, WIPTxn
from app.db.models.genealogy import GenealogyLink
from services.inventory.fifo import fifo_issue
from services.accounting.posting import create_auto_journal

router = APIRouter(prefix="/mes", tags=["mes"], dependencies=[Depends(require_module_enabled("mes"))])

@router.get("/health")
def health():
    return {"ok": True, "service": "mes"}

@router.post("/work-centers")
def create_wc(payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    wc = WorkCenter(code=payload.get("code") or f"WC-{str(uuid.uuid4())[:6].upper()}",
                    name=payload.get("name") or "WorkCenter", meta=payload.get("meta") or {})
    db.add(wc); db.commit(); db.refresh(wc)
    return {"id": wc.id, "code": wc.code}

@router.post("/routings")
def create_routing(payload: dict, db: Session = Depends(get_db)):
    r = Routing(code=payload.get("code") or f"R-{str(uuid.uuid4())[:6].upper()}",
                description=payload.get("description"), meta=payload.get("meta") or {})
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "code": r.code}

@router.get("/production-orders")
def list_production_orders(db: Session = Depends(get_db), limit: int = 200):
    pos = db.query(ProductionOrder).order_by(ProductionOrder.created_at.desc()).limit(limit).all()
    return [{"id": po.id, "number": po.number, "item_id": po.item_id, "qty_planned": float(po.qty_planned), "status": po.status} for po in pos]

@router.get("/production-orders/{po_id}")
def get_production_order(po_id: str, db: Session = Depends(get_db)):
    po = db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "not found")
    mats = db.query(ProductionMaterial).filter(ProductionMaterial.production_order_id == po_id).all()
    return {
        "id": po.id,
        "number": po.number,
        "item_id": po.item_id,
        "routing_id": po.routing_id,
        "qty_planned": float(po.qty_planned),
        "status": po.status,
        "materials": [{"id": m.id, "item_id": m.item_id, "qty_required": float(m.qty_required), "qty_issued": float(m.qty_issued)} for m in mats],
    }

@router.post("/production-orders")
def create_po(payload: dict, db: Session = Depends(get_db)):
    if not payload.get("item_id"):
        raise HTTPException(400, "item_id required")
    po = ProductionOrder(number=payload.get("number") or f"MO-{str(uuid.uuid4())[:8].upper()}",
                         item_id=payload["item_id"],
                         routing_id=payload.get("routing_id"),
                         qty_planned=Decimal(str(payload.get("qty_planned") or 0)),
                         status="PLANNED",
                         meta=payload.get("meta") or {})
    db.add(po); db.commit(); db.refresh(po)
    return {"id": po.id, "number": po.number}

@router.post("/production-orders/{po_id}/release")
def release_po(po_id: str, db: Session = Depends(get_db)):
    po = db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "not found")
    po.status = "RELEASED"
    db.commit()
    return {"ok": True, "status": po.status}

@router.post("/production-orders/{po_id}/issue-materials")
def issue_materials(po_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    """Issue components FIFO into WIP (DR WIP / CR Inventory)."""
    po = db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "production order not found")
    if po.status not in ("RELEASED","IN_PROGRESS","PLANNED"):
        raise HTTPException(409, f"cannot issue in status {po.status}")

    mats = payload.get("materials") or []
    if not mats:
        raise HTTPException(400, "materials required")

    wb = db.query(WIPBalance).filter(WIPBalance.production_order_id == po_id).first()
    if not wb:
        wb = WIPBalance(tenant_id=get_tenant_id(), production_order_id=po_id, fg_item_id=po.item_id, qty=Decimal("0"), total_cost=Decimal("0"), meta={})
        db.add(wb); db.commit(); db.refresh(wb)

    corr = payload.get("correlation_id") or f"ISSUE-{po.number}"
    total_cost = Decimal("0")
    created_txn_ids = []

    for m in mats:
        item_id = m.get("item_id")
        qty = Decimal(str(m.get("qty") or 0))
        if not item_id or qty <= 0:
            raise HTTPException(400, "item_id and qty>0 required")

        item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item:
            raise HTTPException(404, f"item not found: {item_id}")

        unit_cost = m.get("unit_cost")
        if unit_cost is None:
            unit_cost = item.average_cost or item.standard_cost or Decimal("0")
        unit_cost = Decimal(str(unit_cost))

        # FIFO consume balances and create ISSUE_TO_WIP InventoryTxn rows
        try:
            txns = fifo_issue(
                db,
                correlation_id=corr,
                item_id=item_id,
                location_id=m.get("from_location_id"),
                qty=qty,
                actor=principal.username,
                reason=m.get("reason") or "Issue to WIP",
                lot_id=m.get("lot_id"),
                state=m.get("state") or "AVAILABLE",
                unit_cost=unit_cost,
                meta={"production_order_id": po_id},
            )
        except Exception as e:
            raise HTTPException(409, str(e))

        for tx in txns:
            created_txn_ids.append(tx.id)
            ext_cost = Decimal(str(tx.ext_cost or 0))
            total_cost += ext_cost
            db.add(WIPTxn(
                tenant_id=get_tenant_id(),
                production_order_id=po_id,
                txn_type="MAT_ISSUE",
                item_id=item_id,
                qty=tx.qty,
                unit_cost=unit_cost,
                ext_cost=ext_cost,
                reference=corr,
                meta={"inv_txn_id": tx.id, "lot_id": tx.lot_id},
            ))

        pm = db.query(ProductionMaterial).filter(ProductionMaterial.prod_order_id==po_id, ProductionMaterial.item_id==item_id).first()
        if pm:
            pm.qty_issued = (pm.qty_issued or Decimal("0")) + qty

    wb.total_cost = (wb.total_cost or Decimal("0")) + total_cost
    po.status = "IN_PROGRESS" if po.status != "DONE" else po.status
    db.commit()

    create_auto_journal(
        db,
        actor=principal.username,
        description=f"Issue to WIP {po.number}",
        source_module="MES",
        source_document_id=po_id,
        lines=[
            {"account_code":"1400","debit": str(total_cost), "credit": "0", "description":"WIP"},
            {"account_code":"1200","debit": "0", "credit": str(total_cost), "description":"Inventory"},
        ],
    )

    return {"ok": True, "production_order_id": po_id, "issued_cost": float(total_cost), "inventory_txn_ids": created_txn_ids}

@router.post("/production-orders/{po_id}/receive-fg")
def receive_fg(po_id: str, payload: dict, db: Session = Depends(get_db), principal=Depends(get_principal)):
    """Receive finished goods from WIP to inventory (DR Inventory / CR WIP) + genealogy links."""
    po = db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "production order not found")

    qty = Decimal(str(payload.get("qty") or 0))
    if qty <= 0:
        raise HTTPException(400, "qty>0 required")

    item = db.query(InventoryItem).filter(InventoryItem.id == po.item_id).first()
    if not item:
        raise HTTPException(404, "FG item not found")

    wb = db.query(WIPBalance).filter(WIPBalance.production_order_id == po_id).first()
    if not wb:
        raise HTTPException(409, "no WIP balance for this order")

    total_wip_cost = Decimal(str(wb.total_cost or 0))
    total_wip_qty = Decimal(str(wb.qty or 0))
    if total_wip_qty <= 0:
        total_wip_qty = qty
        wb.qty = qty
    unit_cost = (total_wip_cost / total_wip_qty) if total_wip_qty > 0 else Decimal("0")
    ext_cost = unit_cost * qty

    corr = payload.get("correlation_id") or f"FG-{po.number}"
    produced = InventoryTxn(
        correlation_id=corr,
        txn_type="RECEIPT_FROM_WIP",
        item_id=po.item_id,
        from_location_id=None,
        to_location_id=payload.get("to_location_id"),
        lot_id=payload.get("lot_id"),
        handling_unit_id=payload.get("handling_unit_id"),
        state=payload.get("state") or "AVAILABLE",
        qty=qty,
        unit_cost=unit_cost,
        ext_cost=ext_cost,
        uom=payload.get("uom") or item.base_uom,
        actor=principal.username,
        reason=payload.get("reason") or "Receive FG",
        meta={"production_order_id": po_id, "tenant_id": get_tenant_id()},
    )
    db.add(produced); db.commit(); db.refresh(produced)

    # Genealogy: link ALL component issue txns of this PO to this produced txn (lot/serial can be refined later)
    issued = db.query(InventoryTxn).filter(
        InventoryTxn.txn_type == "ISSUE_TO_WIP",
        InventoryTxn.meta["production_order_id"].as_string() == po_id,
    ).all()
    for itx in issued:
        db.add(GenealogyLink(
            tenant_id=get_tenant_id(),
            production_order_id=po_id,
            consumed_txn_id=itx.id,
            produced_txn_id=produced.id,
            item_id=itx.item_id,
            qty=itx.qty,
            meta={"consumed_lot_id": itx.lot_id, "produced_lot_id": produced.lot_id},
        ))

    db.add(WIPTxn(
        tenant_id=get_tenant_id(),
        production_order_id=po_id,
        txn_type="FG_RECEIPT",
        item_id=po.item_id,
        qty=qty,
        unit_cost=unit_cost,
        ext_cost=-ext_cost,
        reference=corr,
        meta={"produced_inv_txn_id": produced.id},
    ))

    wb.total_cost = total_wip_cost - ext_cost
    wb.qty = total_wip_qty - qty
    po.qty_completed = (po.qty_completed or Decimal("0")) + qty
    db.commit()

    create_auto_journal(
        db,
        actor=principal.username,
        description=f"FG receipt {po.number}",
        source_module="MES",
        source_document_id=po_id,
        lines=[
            {"account_code":"1200","debit": str(ext_cost), "credit": "0", "description":"Inventory"},
            {"account_code":"1400","debit": "0", "credit": str(ext_cost), "description":"WIP"},
        ],
    )

    return {"ok": True, "production_order_id": po_id, "received_qty": float(qty), "received_cost": float(ext_cost), "produced_txn_id": produced.id}

@router.post("/production-orders/{po_id}/close")
def close_order(po_id: str, payload: dict | None = None, db: Session = Depends(get_db), principal=Depends(get_principal)):
    """Close order and post remaining WIP as variance."""
    po = db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
    if not po:
        raise HTTPException(404, "production order not found")

    wb = db.query(WIPBalance).filter(WIPBalance.production_order_id == po_id).first()
    remaining = Decimal(str(wb.total_cost or 0)) if wb else Decimal("0")
    if remaining != 0:
        create_auto_journal(
            db,
            actor=principal.username,
            description=f"WIP variance close {po.number}",
            source_module="MES",
            source_document_id=po_id,
            lines=[
                {"account_code":"5100","debit": str(remaining) if remaining>0 else "0", "credit": "0" if remaining>0 else str(-remaining), "description":"Variance"},
                {"account_code":"1400","debit": "0" if remaining>0 else str(-remaining), "credit": str(remaining) if remaining>0 else "0", "description":"WIP"},
            ],
        )
        db.add(WIPTxn(
            tenant_id=get_tenant_id(),
            production_order_id=po_id,
            txn_type="ADJUST",
            item_id=None,
            qty=Decimal("0"),
            unit_cost=Decimal("0"),
            ext_cost=-remaining,
            reference="CLOSE",
            meta={"reason":"variance close"},
        ))
        wb.total_cost = Decimal("0")
        wb.qty = Decimal("0")
        db.commit()

    po.status = "DONE"
    db.commit()
    return {"ok": True, "production_order_id": po_id, "status": po.status, "variance_posted": float(remaining)}
