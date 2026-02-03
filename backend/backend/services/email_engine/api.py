from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal, Principal, require_permissions
from app.db.models.email_engine import EmailAccount, EmailMessage, EmailEvent, EmailAttachment, EmailTriage
from .crypto import encrypt_secret, decrypt_secret
from .smtp_sender import build_message, send_smtp
from .imap_ingest import fetch_unseen_messages, parse_rfc822
from .routing import embed_token_in_subject, extract_token, compute_thread_key
from .storage import save_attachment, read_attachment
from .doc_extract import extract_text_from_pdf_bytes
from .registry import InboundEmailContext, try_auto_create
import uuid
from datetime import datetime, timezone
import os
import urllib.parse


def _public_base_url() -> str:
    return (os.getenv("APP_PUBLIC_BASE_URL") or "http://localhost:8000").rstrip("/")

router = APIRouter(prefix="/email", tags=["email"])
tracking_router = APIRouter(prefix="/t", tags=["email-tracking"])

# ------------- Accounts -------------
@router.get("/account", dependencies=[Depends(require_permissions(["email.read"]))])
def get_my_email_account(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    acc = db.query(EmailAccount).filter(EmailAccount.user_name == p.username).first()
    if not acc:
        return None
    return {
        "id": acc.id,
        "user_name": acc.user_name,
        "email_address": acc.email_address,
        "smtp_host": acc.smtp_host,
        "smtp_port": acc.smtp_port,
        "smtp_tls": acc.smtp_tls,
        "smtp_username": acc.smtp_username,
        "imap_host": acc.imap_host,
        "imap_port": acc.imap_port,
        "imap_tls": acc.imap_tls,
        "imap_username": acc.imap_username,
        "is_active": acc.is_active,
    }

@router.post("/account", dependencies=[Depends(require_permissions(["email.account.manage_own"]))])
def upsert_my_email_account(payload: dict, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    email_address = payload.get("email_address")
    if not email_address:
        raise HTTPException(400, "email_address required")
    acc = db.query(EmailAccount).filter(EmailAccount.user_name == p.username).first()
    if not acc:
        acc = EmailAccount(user_name=p.username, email_address=email_address)
        db.add(acc)

    # Update settings
    acc.email_address = email_address
    acc.smtp_host = payload.get("smtp_host") or acc.smtp_host
    acc.smtp_port = int(payload.get("smtp_port") or acc.smtp_port or 587)
    acc.smtp_tls = bool(payload.get("smtp_tls", True))
    acc.smtp_username = payload.get("smtp_username") or acc.smtp_username
    if payload.get("smtp_password"):
        acc.smtp_password_enc = encrypt_secret(str(payload.get("smtp_password")))

    acc.imap_host = payload.get("imap_host") or acc.imap_host
    acc.imap_port = int(payload.get("imap_port") or acc.imap_port or 993)
    acc.imap_tls = bool(payload.get("imap_tls", True))
    acc.imap_username = payload.get("imap_username") or acc.imap_username
    if payload.get("imap_password"):
        acc.imap_password_enc = encrypt_secret(str(payload.get("imap_password")))

    acc.is_active = bool(payload.get("is_active", True))

    db.commit()
    db.refresh(acc)
    return {"id": acc.id, "ok": True}

@router.post("/account/test", dependencies=[Depends(require_permissions(["email.account.manage_own"]))])
def test_my_email_account(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    acc = db.query(EmailAccount).filter(EmailAccount.user_name == p.username).first()
    if not acc:
        raise HTTPException(404, "No email account configured")
    smtp_pass = decrypt_secret(acc.smtp_password_enc)
    imap_pass = decrypt_secret(acc.imap_password_enc)

    # Test SMTP by NOOP send to self (optional). We only connect+login here.
    try:
        import smtplib
        s = smtplib.SMTP(acc.smtp_host, acc.smtp_port, timeout=15)
        s.ehlo()
        if acc.smtp_tls:
            s.starttls(); s.ehlo()
        if acc.smtp_username:
            s.login(acc.smtp_username, smtp_pass)
        s.quit()
    except Exception as e:
        raise HTTPException(400, f"SMTP test failed: {e}")

    # Test IMAP by login+select
    try:
        import imaplib
        im = imaplib.IMAP4_SSL(acc.imap_host, acc.imap_port) if acc.imap_tls else imaplib.IMAP4(acc.imap_host, acc.imap_port)
        im.login(acc.imap_username, imap_pass)
        im.select("INBOX")
        im.logout()
    except Exception as e:
        raise HTTPException(400, f"IMAP test failed: {e}")

    return {"ok": True}

# ------------- Outbound -------------
@router.post("/send", dependencies=[Depends(require_permissions(["email.send"]))])
def send_email(payload: dict, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    acc = db.query(EmailAccount).filter(EmailAccount.user_name == p.username, EmailAccount.is_active == True).first()  # noqa
    if not acc:
        raise HTTPException(400, "No active email account configured for this user")

    to_emails = payload.get("to") or payload.get("to_emails") or []
    if isinstance(to_emails, str):
        to_emails = [to_emails]
    if not to_emails:
        raise HTTPException(400, "to required")

    subject = payload.get("subject") or ""
    body_text = payload.get("body_text") or ""
    body_html = payload.get("body_html") or ""

    msg_uuid = str(uuid.uuid4())
    subject2 = embed_token_in_subject(subject, msg_uuid)
    corr_token = f"MSG_{msg_uuid}"

    # Build outbound record first
    m = EmailMessage(
        id=msg_uuid,
        direction="OUTBOUND",
        status="QUEUED",
        owner_user_name=p.username,
        from_email=acc.email_address,
        to_emails=list(to_emails),
        cc_emails=list(payload.get("cc") or []),
        bcc_emails=list(payload.get("bcc") or []),
        subject=subject2,
        body_text=body_text,
        body_html=body_html,
        correlation_token=corr_token,
        thread_key=compute_thread_key(acc.email_address, subject2),
        erp_model=payload.get("erp_model"),
        erp_record_id=payload.get("erp_record_id"),
        meta={},
    )
    db.add(m)
    db.commit()
    db.refresh(m)

    attachments_payload = payload.get("attachments") or []
    attachments_for_send = []
    for a in attachments_payload:
        # Expect: {filename, content_base64, content_type}
        filename = a.get("filename") or "attachment"
        content_b64 = a.get("content_base64")
        if not content_b64:
            continue
        import base64
        content = base64.b64decode(content_b64)
        ctype = a.get("content_type") or "application/octet-stream"
        storage_path, sha = save_attachment(content, filename)
        db.add(EmailAttachment(message_id=m.id, filename=filename, content_type=ctype, size_bytes=len(content), sha256=sha, storage_path=storage_path))
        attachments_for_send.append((filename, content, ctype))
    db.commit()

    smtp_pass = decrypt_secret(acc.smtp_password_enc)
    try:
        base = _public_base_url()
        pymsg = build_message(
            from_email=acc.email_address,
            to_emails=list(to_emails),
            subject=subject2,
            body_text=body_text,
            body_html=body_html,
            cc_emails=list(payload.get("cc") or []),
            bcc_emails=list(payload.get("bcc") or []),
            correlation_token=corr_token,
            tracking_open_url=f"{base}/t/open/{msg_uuid}.png",
            tracking_click_base_url=f"{base}/t/c",
            msg_uuid=msg_uuid,
            attachments=attachments_for_send,
        )
        send_smtp(
            host=acc.smtp_host,
            port=acc.smtp_port,
            use_tls=acc.smtp_tls,
            username=acc.smtp_username,
            password=smtp_pass,
            msg=pymsg,
        )
        m.status = "SENT"
        m.sent_at = datetime.now(timezone.utc)
        m.smtp_message_id = str(pymsg.get("Message-ID") or "")
        db.add(m)
        db.commit()
    except Exception as e:
        m.status = "FAILED"
        m.error = str(e)
        db.add(m)
        db.commit()
        raise HTTPException(400, f"Send failed: {e}")

    return {"id": m.id, "status": m.status, "smtp_message_id": m.smtp_message_id}

@router.get("/sent")
def list_sent(db: Session = Depends(get_db), p: Principal = Depends(get_principal), limit: int = 50):
    qs = db.query(EmailMessage).filter(EmailMessage.owner_user_name == p.username, EmailMessage.direction == "OUTBOUND").order_by(EmailMessage.created_at.desc()).limit(limit).all()
    return [{"id": m.id, "status": m.status, "subject": m.subject, "to": m.to_emails, "sent_at": m.sent_at} for m in qs]

# ------------- Inbound Sync (manual trigger; you can schedule it) -------------
@router.post("/sync", dependencies=[Depends(require_permissions(["email.read"]))])
def sync_inbox(db: Session = Depends(get_db), p: Principal = Depends(get_principal), limit: int = 25):
    acc = db.query(EmailAccount).filter(EmailAccount.user_name == p.username, EmailAccount.is_active == True).first()  # noqa
    if not acc:
        raise HTTPException(400, "No active email account configured for this user")
    imap_pass = decrypt_secret(acc.imap_password_enc)

    items = fetch_unseen_messages(
        host=acc.imap_host,
        port=acc.imap_port,
        use_tls=acc.imap_tls,
        username=acc.imap_username,
        password=imap_pass,
        limit=limit,
    )

    imported = 0
    for uid, raw in items:
        parsed = parse_rfc822(raw)
        smtp_id = parsed.get("smtp_message_id") or ""
        # dedupe by smtp_message_id if present
        if smtp_id and db.query(EmailMessage).filter(EmailMessage.smtp_message_id == smtp_id).first():
            continue

        subj = parsed.get("subject") or ""
        tok = parsed.get("x_erp_msg") or extract_token(subj) or extract_token(parsed.get("body_text") or "") or extract_token(parsed.get("body_html") or "")
        thread_key = compute_thread_key(parsed.get("from_email") or "", subj)

        msg = EmailMessage(
            direction="INBOUND",
            status="RECEIVED",
            owner_user_name=p.username,
            from_email=parsed.get("from_email") or "",
            to_emails=[parsed.get("to_raw") or ""],
            cc_emails=[parsed.get("cc_raw") or ""],
            subject=subj,
            body_text=parsed.get("body_text") or "",
            body_html=parsed.get("body_html") or "",
            smtp_message_id=smtp_id or None,
            in_reply_to=parsed.get("in_reply_to"),
            references=parsed.get("references") or [],
            correlation_token=tok,
            thread_key=thread_key,
            received_at=datetime.now(timezone.utc),
            meta={"imap_uid": uid.decode() if isinstance(uid, (bytes, bytearray)) else str(uid)},
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # Attachments + (best-effort) text extraction
        attachment_text_parts: list[str] = []
        for a in (parsed.get("attachments") or []):
            content = a.get("content") or b""
            filename = a.get("filename") or "attachment"
            ctype = a.get("content_type") or "application/octet-stream"
            if ctype == "application/pdf" or (filename.lower().endswith(".pdf")):
                attachment_text_parts.append(extract_text_from_pdf_bytes(content))
            storage_path, sha = save_attachment(content, filename)
            db.add(EmailAttachment(message_id=msg.id, filename=filename, content_type=ctype, size_bytes=len(content), sha256=sha, storage_path=storage_path))
        db.commit()
        attachment_text = "\n".join([t for t in attachment_text_parts if t])

        # Routing attempt: if token matches outbound, link record
        linked = False
        if tok:
            out = db.query(EmailMessage).filter(EmailMessage.direction == "OUTBOUND", EmailMessage.correlation_token == tok).order_by(EmailMessage.created_at.desc()).first()
            if out and out.erp_model and out.erp_record_id:
                msg.erp_model = out.erp_model
                msg.erp_record_id = out.erp_record_id
                linked = True
                # mark reply event
                db.add(EmailEvent(message_id=out.id, event_type="REPLY", data={"inbound_message_id": msg.id}))
                db.commit()

        if not linked:
            # Try registered automations (best-effort). If no confident match, triage.
            ctx = InboundEmailContext(
                owner_user_name=msg.owner_user_name,
                from_email=msg.from_email,
                subject=msg.subject,
                body_text=msg.body_text,
                attachment_text=attachment_text,
            )
            link = try_auto_create(db, ctx)

            if link:
                msg.erp_model = link.erp_model
                msg.erp_record_id = link.erp_record_id
                db.add(msg)
                db.commit()
            else:
                db.add(EmailTriage(inbound_message_id=msg.id, reason="UNROUTED", confidence=0, meta={"note": "No token/thread match or automation match"}))
                db.commit()

        imported += 1

    return {"ok": True, "imported": imported}

@router.get("/triage", dependencies=[Depends(require_permissions(["email.triage.view"]))])
def list_triage(
    db: Session = Depends(get_db),
    p: Principal = Depends(get_principal),
    status: str = "OPEN",
    limit: int = 50,
):
    # Only show triage items for inbound emails owned by this user (multi-user safety).
    q = (
        db.query(EmailTriage, EmailMessage)
        .join(EmailMessage, EmailMessage.id == EmailTriage.inbound_message_id)
        .filter(EmailMessage.owner_user_name == p.username)
    )
    if status:
        q = q.filter(EmailTriage.status == status)
    rows = q.order_by(EmailTriage.created_at.desc()).limit(limit).all()

    out = []
    for t, m in rows:
        out.append(
            {
                "id": t.id,
                "status": t.status,
                "reason": t.reason,
                "confidence": t.confidence,
                "inbound_message_id": t.inbound_message_id,
                "created_at": t.created_at,
                "from": m.from_email,
                "subject": m.subject,
                "received_at": m.received_at,
                "suggested_model": t.suggested_model,
                "suggested_record_id": t.suggested_record_id,
            }
        )
    return out


@router.post("/triage/{triage_id}/attach", dependencies=[Depends(require_permissions(["email.triage.attach"]))])
def triage_attach(
    triage_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    p: Principal = Depends(get_principal),
):
    """Manually attach a triage item to an ERP record and resolve it.

    payload: {erp_model: str, erp_record_id: str}
    """
    t = db.query(EmailTriage).filter(EmailTriage.id == triage_id).first()
    if not t:
        raise HTTPException(404, "triage not found")

    m = db.query(EmailMessage).filter(EmailMessage.id == t.inbound_message_id).first()
    if not m or m.owner_user_name != p.username:
        raise HTTPException(404, "triage not found")

    erp_model = (payload.get("erp_model") or "").strip()
    erp_record_id = (payload.get("erp_record_id") or "").strip()
    if not erp_model or not erp_record_id:
        raise HTTPException(400, "erp_model and erp_record_id required")

    m.erp_model = erp_model
    m.erp_record_id = erp_record_id
    t.status = "RESOLVED"
    t.meta = {**(t.meta or {}), "resolved_by": p.username, "resolved_action": "ATTACH", "resolved_at": datetime.now(timezone.utc).isoformat()}
    db.add(m); db.add(t)
    db.commit()
    return {"ok": True, "inbound_message_id": m.id, "erp_model": m.erp_model, "erp_record_id": m.erp_record_id}


@router.post("/triage/{triage_id}/create/ap-invoice", dependencies=[Depends(require_permissions(["email.triage.create_ap_invoice"]))])
def triage_create_ap_invoice(
    triage_id: str,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    p: Principal = Depends(get_principal),
):
    """Force AP invoice creation from a triage email.

    Optional payload: {po_number: "12345"} to override matching.
    """
    t = db.query(EmailTriage).filter(EmailTriage.id == triage_id).first()
    if not t:
        raise HTTPException(404, "triage not found")
    m = db.query(EmailMessage).filter(EmailMessage.id == t.inbound_message_id).first()
    if not m or m.owner_user_name != p.username:
        raise HTTPException(404, "triage not found")

    po_number = None
    if payload:
        po_number = payload.get("po_number")


    # Recompute attachment text (best-effort) from stored attachments
    attachment_text_parts: list[str] = []
    for a in db.query(EmailAttachment).filter(EmailAttachment.message_id == m.id).all():
        if (a.content_type == "application/pdf") or (a.filename.lower().endswith(".pdf")):
            try:
                content = read_attachment(a.storage_path)
                attachment_text_parts.append(extract_text_from_pdf_bytes(content))
            except Exception:
                pass
    attachment_text = "\n".join([t for t in attachment_text_parts if t])

    # Call AP adapter directly (kept behind adapters/ to avoid module conflicts)
    try:
        from .adapters import ap as ap_adapter

        inv = ap_adapter.try_create_ap_invoice_from_email(
            db=db,
            owner_user_name=m.owner_user_name,
            from_email=m.from_email,
            subject=m.subject,
            body_text=m.body_text,
            attachment_text=attachment_text,
            forced_po_number=po_number,
        )
    except Exception:
        inv = None

    if not inv:
        raise HTTPException(400, "Unable to create AP invoice (need a PO match + vendor match)")

    m.erp_model = "ap.invoice"
    m.erp_record_id = str(inv.id)
    t.status = "RESOLVED"
    t.meta = {**(t.meta or {}), "resolved_by": p.username, "resolved_action": "CREATE_AP_INVOICE", "resolved_at": datetime.now(timezone.utc).isoformat()}
    db.add(m); db.add(t)
    db.commit()
    return {"ok": True, "erp_model": m.erp_model, "erp_record_id": m.erp_record_id}


@router.post("/triage/{triage_id}/create/sales-order", dependencies=[Depends(require_permissions(["email.triage.create_sales_order"]))])
def triage_create_sales_order(
    triage_id: str,
    db: Session = Depends(get_db),
    p: Principal = Depends(get_principal),
):
    """Force Sales Order creation from a triage email (customer must be recognized)."""
    t = db.query(EmailTriage).filter(EmailTriage.id == triage_id).first()
    if not t:
        raise HTTPException(404, "triage not found")
    m = db.query(EmailMessage).filter(EmailMessage.id == t.inbound_message_id).first()
    if not m or m.owner_user_name != p.username:
        raise HTTPException(404, "triage not found")

    # Recompute attachment text (best-effort) from stored attachments
    attachment_text_parts: list[str] = []
    for a in db.query(EmailAttachment).filter(EmailAttachment.message_id == m.id).all():
        if (a.content_type == "application/pdf") or (a.filename.lower().endswith(".pdf")):
            try:
                content = read_attachment(a.storage_path)
                attachment_text_parts.append(extract_text_from_pdf_bytes(content))
            except Exception:
                pass
    attachment_text = "\n".join([t for t in attachment_text_parts if t])

    try:
        from .adapters import sales as sales_adapter

        so = sales_adapter.try_create_sales_order_from_email(
            db=db,
            owner_user_name=m.owner_user_name,
            from_email=m.from_email,
            subject=m.subject,
            body_text=m.body_text,
            attachment_text=attachment_text,
        )
    except Exception:
        so = None

    if not so:
        raise HTTPException(400, "Unable to create Sales Order (customer sender not recognized)")

    m.erp_model = "sales.order"
    m.erp_record_id = str(so.id)
    t.status = "RESOLVED"
    t.meta = {**(t.meta or {}), "resolved_by": p.username, "resolved_action": "CREATE_SALES_ORDER", "resolved_at": datetime.now(timezone.utc).isoformat()}
    db.add(m); db.add(t)
    db.commit()
    return {"ok": True, "erp_model": m.erp_model, "erp_record_id": m.erp_record_id}


@router.post("/triage/{triage_id}/resolve", dependencies=[Depends(require_permissions(["email.triage.resolve"]))])
def triage_resolve(
    triage_id: str,
    db: Session = Depends(get_db),
    p: Principal = Depends(get_principal),
):
    t = db.query(EmailTriage).filter(EmailTriage.id == triage_id).first()
    if not t:
        raise HTTPException(404, "triage not found")
    m = db.query(EmailMessage).filter(EmailMessage.id == t.inbound_message_id).first()
    if not m or m.owner_user_name != p.username:
        raise HTTPException(404, "triage not found")
    t.status = "RESOLVED"
    t.meta = {**(t.meta or {}), "resolved_by": p.username, "resolved_action": "RESOLVE", "resolved_at": datetime.now(timezone.utc).isoformat()}
    db.add(t)
    db.commit()
    return {"ok": True}


# ------------- Tracking endpoints -------------
# 1x1 transparent PNG
_PIXEL = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\x0d\n\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

@tracking_router.get("/open/{msg_id}.png")
def track_open(msg_id: str, db: Session = Depends(get_db)):
    m = db.query(EmailMessage).filter(EmailMessage.id == msg_id).first()
    if m:
        db.add(EmailEvent(message_id=m.id, event_type="OPEN", data={}))
        db.commit()
    return Response(content=_PIXEL, media_type="image/png")

@tracking_router.get("/c/{msg_id}/{link_id}")
def track_click(msg_id: str, link_id: str, u: str, db: Session = Depends(get_db)):
    # u = urlencoded destination (keep simple for now)
    m = db.query(EmailMessage).filter(EmailMessage.id == msg_id).first()
    if m:
        db.add(EmailEvent(message_id=m.id, event_type="CLICK", data={"link_id": link_id, "u": u}))
        db.commit()
    dest = urllib.parse.unquote(u)
    return RedirectResponse(url=dest, status_code=302)
