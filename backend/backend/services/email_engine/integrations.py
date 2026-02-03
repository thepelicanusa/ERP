from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from email.utils import parseaddr
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db.models.purchasing import PurchaseOrder, Vendor, PurchaseOrderLine, PurchaseReceipt, PurchaseReceiptLine
from app.db.models.accounting import APVendor, APInvoice, APInvoiceLine
from app.db.models.sales import Customer, SalesOrder, SalesOrderLine

# Matches "PO 1234", "PO-1234", "PO1234", "P.O. 1234" (keeps it conservative)
PO_RE = re.compile(r"\bP\.?\s*O\.?[-\s]*([A-Za-z0-9]{3,32})\b", re.IGNORECASE)

# Very lightweight "total" parser (Phase 1)
TOTAL_RE = re.compile(
    r"(?:(?:invoice\s*)?total|amount\s*due|balance\s*due|grand\s*total)\s*[:\-]?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
    re.IGNORECASE,
)

def _email_only(raw_from: str) -> str:
    return (parseaddr(raw_from)[1] or "").strip().lower()


def extract_po_number(text: str) -> Optional[str]:
    if not text:
        return None
    m = PO_RE.search(text)
    if not m:
        return None
    return m.group(1).strip()


def extract_total_amount(text: str) -> Optional[Decimal]:
    """Best-effort total extraction from email/PDF text.

    This is intentionally conservative (Phase 1). If we can't find a clear total,
    we return None and fall back to triage.
    """
    if not text:
        return None
    m = TOTAL_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(",", "").strip()
    try:
        return Decimal(raw)
    except Exception:
        return None


def _guess_due_date(payment_terms: str | None) -> date:
    # Very small starter: NET30/NET15/NET60
    pt = (payment_terms or "NET30").upper().strip()
    days = 30
    if "15" in pt:
        days = 15
    elif "60" in pt:
        days = 60
    return date.today() + timedelta(days=days)


def _pick_best_po(candidates: Sequence[PurchaseOrder], total: Optional[Decimal]) -> Optional[PurchaseOrder]:
    if not candidates:
        return None
    if total is None:
        # If we don't know total, don't auto-pick among multiple
        if len(candidates) == 1:
            return candidates[0]
        return None
    # pick closest by absolute difference, but require within tolerance
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
    if best is None:
        return None
    # tolerance: within 5% or $25, whichever is larger
    po_total = Decimal(str(best.total_amount))
    tol = max(po_total * Decimal("0.05"), Decimal("25"))
    if best_diff is not None and best_diff <= tol:
        return best
    return None


def _candidate_pos_for_vendor(db: Session, vendor_id: str) -> list[PurchaseOrder]:
    # last ~120 days, not cancelled/closed
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



def _receipt_status_for_po(db: Session, po: PurchaseOrder) -> dict:
    """3-way match stub: summarize receiving status for a PO.

    Returns:
      {
        "has_receipt": bool,
        "receipt_count": int,
        "qty_ok": bool | None,
        "qty_variances": [{"po_line_id":..., "ordered":..., "received":...}],
      }
    """
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
    rlines = (
        db.query(PurchaseReceiptLine)
        .filter(PurchaseReceiptLine.receipt_id.in_(receipt_ids))
        .all()
    )

    received_by_po_line: dict[str, Decimal] = {}
    for rl in rlines:
        try:
            q = Decimal(str(rl.quantity_received))
        except Exception:
            q = Decimal("0")
        received_by_po_line[rl.po_line_id] = received_by_po_line.get(rl.po_line_id, Decimal("0")) + q

    po_lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.po_id == po.id)
        .all()
    )

    variances = []
    qty_ok = True
    for pl in po_lines:
        ordered = Decimal(str(pl.quantity_ordered))
        received = received_by_po_line.get(pl.id, Decimal("0"))
        # simple tolerance: allow 0.0001 difference for decimal/rounding
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

    return {
        "has_receipt": True,
        "receipt_count": len(receipts),
        "qty_ok": qty_ok,
        "qty_variances": variances,
    }


def _apply_ap_match_flags(
    *,
    inv: APInvoice,
    po: PurchaseOrder,
    extracted_total: Decimal | None,
    receipt_summary: dict,
) -> None:
    """Apply tolerance rules + variance flags into invoice.meta and approval_status."""
    meta = dict(inv.meta or {})
    meta["match"] = meta.get("match") or {}
    meta["match"]["po_total"] = str(po.total_amount)
    if extracted_total is not None:
        meta["match"]["extracted_total"] = str(extracted_total)
        try:
            po_total = Decimal(str(po.total_amount))
            diff = extracted_total - po_total
            meta["match"]["total_diff"] = str(diff)
            meta["match"]["total_diff_abs"] = str(abs(diff))
            # tolerance: within 2% or $10, whichever is larger (invoice totals can differ slightly)
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

    # Receipt rule: if no receipt or qty not ok, require review/hold
    if not receipt_summary.get("has_receipt"):
        needs_review = True
        reasons.append("MISSING_RECEIPT")
    elif receipt_summary.get("qty_ok") is False:
        needs_review = True
        reasons.append("RECEIPT_QTY_SHORT")

    # Total variance rule (if we could extract a total)
    within = meta["match"].get("total_within_tolerance")
    if within is False:
        needs_review = True
        reasons.append("TOTAL_VARIANCE")

    meta["match"]["review_required"] = needs_review
    meta["match"]["review_reasons"] = reasons

    # keep status as PENDING, but escalate approval_status for workflow
    if needs_review:
        inv.approval_status = "REQUIRES_REVIEW"
        inv.status = "PENDING"
    inv.meta = meta

def _create_invoice_lines_from_po(db: Session, inv: APInvoice, po: PurchaseOrder) -> None:
    # Clear any existing lines (should be none for new invoice, but safe)
    db.query(APInvoiceLine).filter(APInvoiceLine.invoice_id == inv.id).delete()
    po_lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.po_id == po.id)
        .order_by(PurchaseOrderLine.line_number.asc())
        .all()
    )
    ln = 1
    for pl in po_lines:
        qty = Decimal(str(pl.quantity_ordered))
        unit = Decimal(str(pl.unit_price))
        total = Decimal(str(pl.line_total))
        db.add(
            APInvoiceLine(
                invoice_id=inv.id,
                line_number=ln,
                description=(pl.description or "").strip()[:512] or f"PO line {pl.line_number}",
                quantity=qty,
                unit_price=unit,
                line_total=total,
                item_id=getattr(pl, "item_id", None),
            )
        )
        ln += 1


def try_create_ap_invoice_from_email(
    *,
    db: Session,
    inbound_message_id: str,
    from_raw: str,
    subject: str,
    body_text: str,
    body_html: str,
    attachment_text: str = "",
    override_po_number: str | None = None,
) -> Optional[dict]:
    """Best-effort AP automation.

    Creates a draft APInvoice linked to a PurchaseOrder when we can confidently
    identify both the vendor and PO number OR match a PO by vendor+total.
    """

    from_email = _email_only(from_raw)
    if not from_email:
        return None

    haystack = "\n".join([subject or "", body_text or "", body_html or "", attachment_text or ""])
    po_num = (override_po_number or "").strip() or extract_po_number(haystack)
    extracted_total = extract_total_amount(haystack)

    # 1) Identify vendor
    ap_vendor = db.query(APVendor).filter(APVendor.email == from_email).first()
    purch_vendor = None
    if not ap_vendor:
        # Try matching purchasing vendor by sender email, then map to AP vendor via email
        purch_vendor = db.query(Vendor).filter(Vendor.email == from_email).first()
        if purch_vendor and purch_vendor.email:
            ap_vendor = db.query(APVendor).filter(APVendor.email == purch_vendor.email).first()

    if not ap_vendor and not purch_vendor:
        return None

    # 2) Find PO
    po = None
    if po_num:
        po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_num).first()
        if not po:
            return None
    else:
        # vendor+total heuristic
        total = extracted_total
        vendor_id = None
        if purch_vendor:
            vendor_id = purch_vendor.id
        else:
            # If we only have APVendor, attempt to map to purchasing vendor by email
            pv = db.query(Vendor).filter(Vendor.email == ap_vendor.email).first()
            vendor_id = pv.id if pv else None
        if not vendor_id:
            return None
        cands = _candidate_pos_for_vendor(db, vendor_id)
        po = _pick_best_po(cands, total)
        if not po:
            return None

    # Ensure AP vendor exists (required)
    if not ap_vendor:
        # If we found the PO but still no AP vendor, try PO's vendor email
        pv = db.query(Vendor).filter(Vendor.id == po.vendor_id).first()
        if pv and pv.email:
            ap_vendor = db.query(APVendor).filter(APVendor.email == pv.email).first()
    if not ap_vendor:
        return None

    inv = APInvoice(
        invoice_number=f"APINV-{po.po_number}-{inbound_message_id[:8]}",
        vendor_invoice_number=None,
        vendor_id=ap_vendor.id,
        invoice_date=date.today(),
        due_date=_guess_due_date(getattr(ap_vendor, "payment_terms", "NET30")),
        payment_terms=getattr(ap_vendor, "payment_terms", "NET30"),
        subtotal=Decimal(str(po.subtotal)),
        tax_amount=Decimal(str(po.tax_amount)),
        shipping_amount=Decimal(str(po.shipping_amount)),
        discount_amount=Decimal("0"),
        total_amount=Decimal(str(po.total_amount)),
        paid_amount=Decimal("0"),
        balance=Decimal(str(po.total_amount)),
        currency=getattr(ap_vendor, "currency", getattr(po, "currency", "USD")),
        status="PENDING",
        approval_status="PENDING",
        source_document_type="PURCHASE_ORDER",
        source_document_id=po.id,
        description=f"Auto-created from inbound email for PO {po.po_number}",
        meta={"created_from_email": inbound_message_id, "po_number": po.po_number, "sender": from_email},
    )
    db.add(inv)
    db.flush()  # get inv.id

    _create_invoice_lines_from_po(db, inv, po)
    db.flush()

    # Tolerance rules + 3-way match stub (receipts)
    receipt_summary = _receipt_status_for_po(db, po)
    _apply_ap_match_flags(inv=inv, po=po, extracted_total=extracted_total, receipt_summary=receipt_summary)
    db.flush()

    return {"erp_model": "APInvoice", "erp_record_id": inv.id, "po_id": po.id, "match": inv.meta.get("match")}


def try_create_sales_order_from_email(
    *,
    db: Session,
    inbound_message_id: str,
    from_raw: str,
    subject: str,
    body_text: str,
    body_html: str,
    attachment_text: str = "",
) -> Optional[dict]:
    """Best-effort Sales automation.

    Creates a draft SalesOrder when we can identify a known customer sender.
    Line extraction is left for a later phase.
    """

    from_email = _email_only(from_raw)
    if not from_email:
        return None

    customer = db.query(Customer).filter(Customer.email == from_email).first()
    if not customer:
        return None

    haystack = "\n".join([subject or "", body_text or "", body_html or "", attachment_text or ""])
    customer_po = extract_po_number(haystack) or None

    # Required addresses on the SalesOrder model; fall back to customer defaults or placeholders.
    ship1 = customer.shipping_address_line1 or customer.billing_address_line1 or "UNKNOWN"
    ship_city = customer.shipping_city or customer.billing_city or "UNKNOWN"
    ship_state = customer.shipping_state or customer.billing_state or "NA"
    ship_zip = customer.shipping_postal_code or customer.billing_postal_code or "00000"

    bill1 = customer.billing_address_line1 or ship1
    bill_city = customer.billing_city or ship_city
    bill_state = customer.billing_state or ship_state
    bill_zip = customer.billing_postal_code or ship_zip

    so = SalesOrder(
        order_number=f"SO-{inbound_message_id[:8]}",
        order_date=date.today(),
        customer_id=customer.id,
        customer_po=customer_po,
        customer_contact=customer.primary_contact,
        ship_to_name=customer.customer_name,
        ship_to_address_line1=ship1,
        ship_to_address_line2=customer.shipping_address_line2,
        ship_to_city=ship_city,
        ship_to_state=ship_state,
        ship_to_postal_code=ship_zip,
        ship_to_country=customer.shipping_country or "USA",
        bill_to_name=customer.customer_name,
        bill_to_address_line1=bill1,
        bill_to_address_line2=customer.billing_address_line2,
        bill_to_city=bill_city,
        bill_to_state=bill_state,
        bill_to_postal_code=bill_zip,
        bill_to_country=customer.billing_country or "USA",
        subtotal=Decimal("0"),
        discount_amount=Decimal("0"),
        tax_amount=Decimal("0"),
        shipping_amount=Decimal("0"),
        total_amount=Decimal("0"),
        currency="USD",
        payment_terms=customer.payment_terms or "NET30",
        shipping_method="STANDARD",
        carrier=None,
        carrier_service=None,
        requested_ship_date=None,
        promised_ship_date=None,
        actual_ship_date=None,
        priority="NORMAL",
        status="PENDING",
        allocation_status="PENDING",
        picking_status="PENDING",
        packing_status="PENDING",
        meta={"created_from_email": inbound_message_id, "sender": from_email},
    )
    db.add(so)
    db.flush()

    # Placeholder line to make the SO editable. Real line extraction comes later.
    sol = SalesOrderLine(
        order_id=so.id,
        line_number=1,
        item_id="MISC",
        description="Auto-created (line details to be reviewed)",
        quantity_ordered=Decimal("1"),
        uom="EA",
        unit_price=Decimal("0"),
        discount_percentage=Decimal("0"),
        line_total=Decimal("0"),
        requested_date=None,
        promised_date=None,
        shipped_date=None,
        line_status="OPEN",
        meta={},
    )
    db.add(sol)
    db.flush()

    return {"erp_model": "SalesOrder", "erp_record_id": so.id}
