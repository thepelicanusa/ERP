from __future__ import annotations

"""AP adapter for the email engine.

All AP-specific imports live in this file only, to prevent cross-module
conflicts in a multi-module ERP.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db.models.purchasing import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseReceipt,
    PurchaseReceiptLine,
    Vendor,
)
from app.db.models.accounting import APInvoice, APInvoiceLine, APVendor

from ..core_extract import email_only, extract_po_number, extract_total_amount


def try_create_ap_invoice_from_email(
    *,
    db: Session,
    owner_user_name: str,
    from_email: str,
    subject: str,
    body_text: str,
    attachment_text: str,
    forced_po_number: str | None = None,
) -> Optional[APInvoice]:
    """Best-effort creation of a draft AP Invoice from an inbound email.

    Strategy:
      1) Extract PO number from subject/body/attachments (or accept forced PO)
      2) Match vendor by sender email
      3) Create invoice lines from PO lines
      4) Apply tolerance rules + receipt stub flags
    """

    sender = email_only(from_email)
    if not sender:
        return None

    # Resolve vendor
    ap_vendor = db.query(APVendor).filter(APVendor.email == sender).first()
    vendor = None
    if ap_vendor and getattr(ap_vendor, "vendor_id", None):
        vendor = db.query(Vendor).filter(Vendor.id == ap_vendor.vendor_id).first()
    if vendor is None:
        vendor = db.query(Vendor).filter(Vendor.email == sender).first()
    if vendor is None:
        return None

    combined_text = "\n".join([subject or "", body_text or "", attachment_text or ""]).strip()

    po_number = forced_po_number or extract_po_number(combined_text)
    extracted_total = extract_total_amount(combined_text)

    po: PurchaseOrder | None = None
    if po_number:
        po = (
            db.query(PurchaseOrder)
            .filter(PurchaseOrder.po_number == po_number, PurchaseOrder.vendor_id == vendor.id)
            .first()
        )

    if po is None:
        # Fallback: pick PO by vendor + amount heuristics (conservative)
        candidates = _candidate_pos_for_vendor(db, vendor.id)
        po = _pick_best_po(candidates, extracted_total)
        if po is None:
            return None

    # Create invoice
    inv = APInvoice(
        vendor_id=getattr(ap_vendor, "id", None) or getattr(vendor, "id"),
        status="DRAFT",
        invoice_date=date.today(),
        due_date=_guess_due_date(getattr(ap_vendor, "payment_terms", None)),
        currency=getattr(po, "currency", "USD"),
        subtotal_amount=po.subtotal_amount,
        tax_amount=po.tax_amount,
        shipping_amount=getattr(po, "shipping_amount", 0),
        total_amount=po.total_amount,
        balance_amount=po.total_amount,
        meta={"created_from_email": True, "email_owner": owner_user_name, "po_id": po.id},
    )
    db.add(inv)
    db.flush()  # ensure inv.id

    # Map PO lines -> AP invoice lines
    po_lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).order_by(PurchaseOrderLine.id).all()
    for pl in po_lines:
        line = APInvoiceLine(
            invoice_id=inv.id,
            product_id=getattr(pl, "product_id", None),
            description=getattr(pl, "description", "") or getattr(pl, "product_name", ""),
            quantity=getattr(pl, "quantity_ordered", 0),
            unit_price=getattr(pl, "unit_price", 0),
            line_total=getattr(pl, "line_total", None) or (getattr(pl, "quantity_ordered", 0) * getattr(pl, "unit_price", 0)),
            meta={"po_line_id": pl.id, "po_id": po.id},
        )
        db.add(line)

    receipt_summary = _receipt_status_for_po(db, po)
    _apply_ap_match_flags(inv=inv, po=po, extracted_total=extracted_total, receipt_summary=receipt_summary)

    db.flush()
    return inv


def _guess_due_date(payment_terms: str | None) -> date:
    pt = (payment_terms or "NET30").upper().strip()
    days = 30
    if "15" in pt:
        days = 15
    elif "60" in pt:
        days = 60
    return date.today() + timedelta(days=days)


def _candidate_pos_for_vendor(db: Session, vendor_id: str) -> list[PurchaseOrder]:
    cutoff = date.today() - timedelta(days=120)
    return (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.vendor_id == vendor_id,
            PurchaseOrder.po_date >= cutoff,
            PurchaseOrder.status.notin_(["CANCELLED", "CLOSED"]),
        )
        .order_by(PurchaseOrder.po_date.desc())
        .limit(25)
        .all()
    )


def _pick_best_po(candidates: Sequence[PurchaseOrder], total: Optional[Decimal]) -> Optional[PurchaseOrder]:
    if not candidates:
        return None
    if total is None:
        return candidates[0] if len(candidates) == 1 else None

    best = None
    best_diff = None
    for po in candidates:
        try:
            po_total = Decimal(str(po.total_amount))
        except Exception:
            continue
        diff = abs(po_total - total)
        if best is None or diff < best_diff:
            best = po
            best_diff = diff
    if best is None or best_diff is None:
        return None

    po_total = Decimal(str(best.total_amount))
    tol = max(po_total * Decimal("0.05"), Decimal("25"))
    return best if best_diff <= tol else None


def _receipt_status_for_po(db: Session, po: PurchaseOrder) -> dict:
    receipts = (
        db.query(PurchaseReceipt)
        .filter(PurchaseReceipt.po_id == po.id)
        .order_by(PurchaseReceipt.receipt_date.desc())
        .limit(10)
        .all()
    )
    if not receipts:
        return {"has_receipt": False, "receipt_count": 0, "qty_ok": None, "qty_variances": []}

    receipt_ids = [r.id for r in receipts]
    rlines = db.query(PurchaseReceiptLine).filter(PurchaseReceiptLine.receipt_id.in_(receipt_ids)).all()

    received_by_po_line: dict[str, Decimal] = {}
    for rl in rlines:
        try:
            q = Decimal(str(rl.quantity_received))
        except Exception:
            q = Decimal("0")
        received_by_po_line[rl.po_line_id] = received_by_po_line.get(rl.po_line_id, Decimal("0")) + q

    po_lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).all()
    variances = []
    qty_ok = True
    for pl in po_lines:
        ordered = Decimal(str(pl.quantity_ordered))
        received = received_by_po_line.get(pl.id, Decimal("0"))
        if received + Decimal("0.0001") < ordered:
            qty_ok = False
            variances.append(
                {
                    "po_line_id": pl.id,
                    "line_number": getattr(pl, "line_number", None),
                    "ordered": str(ordered),
                    "received": str(received),
                }
            )

    return {"has_receipt": True, "receipt_count": len(receipts), "qty_ok": qty_ok, "qty_variances": variances}


def _apply_ap_match_flags(*, inv: APInvoice, po: PurchaseOrder, extracted_total: Decimal | None, receipt_summary: dict) -> None:
    meta = dict(inv.meta or {})
    meta.setdefault("match", {})
    meta["match"]["po_total"] = str(po.total_amount)
    if extracted_total is not None:
        meta["match"]["extracted_total"] = str(extracted_total)
        try:
            po_total = Decimal(str(po.total_amount))
            diff = extracted_total - po_total
            meta["match"]["total_diff"] = str(diff)
            meta["match"]["total_diff_abs"] = str(abs(diff))
            tol = max(po_total * Decimal("0.02"), Decimal("10"))
            meta["match"]["total_tolerance"] = str(tol)
            meta["match"]["total_within_tolerance"] = bool(abs(diff) <= tol)
        except Exception:
            meta["match"]["total_within_tolerance"] = None
    else:
        meta["match"]["extracted_total"] = None

    meta["match"]["receipts"] = receipt_summary

    needs_review = False
    reasons = []

    if not receipt_summary.get("has_receipt"):
        needs_review = True
        reasons.append("MISSING_RECEIPT")
    elif receipt_summary.get("qty_ok") is False:
        needs_review = True
        reasons.append("RECEIPT_QTY_SHORT")

    twt = meta["match"].get("total_within_tolerance")
    if twt is False:
        needs_review = True
        reasons.append("TOTAL_VARIANCE")

    meta["match"]["review_required"] = needs_review
    meta["match"]["review_reasons"] = reasons
    inv.meta = meta
    if needs_review:
        # If your APInvoice model has an approval_status field, set it.
        if hasattr(inv, "approval_status"):
            inv.approval_status = "REQUIRES_REVIEW"
