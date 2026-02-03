from __future__ import annotations

import imaplib
import email
from email.message import Message
from typing import Optional, Tuple, List
from datetime import datetime, timezone

def _imap_connect(host: str, port: int, use_tls: bool):
    if use_tls:
        return imaplib.IMAP4_SSL(host, port)
    return imaplib.IMAP4(host, port)

def fetch_unseen_messages(
    *,
    host: str,
    port: int,
    use_tls: bool,
    username: str,
    password: str,
    mailbox: str = "INBOX",
    limit: int = 50,
) -> list[tuple[bytes, bytes]]:
    """
    Returns list of tuples: (uid, raw_rfc822_bytes)
    Uses UID + UNSEEN so it can be safely repeated with local dedupe.
    """
    imap = _imap_connect(host, port, use_tls)
    try:
        imap.login(username, password)
        imap.select(mailbox)
        typ, data = imap.uid("search", None, "UNSEEN")
        if typ != "OK":
            return []
        uids = (data[0] or b"").split()
        uids = uids[:limit]
        out: list[tuple[bytes, bytes]] = []
        for uid in uids:
            typ2, msgdata = imap.uid("fetch", uid, "(RFC822)")
            if typ2 != "OK" or not msgdata:
                continue
            raw = msgdata[0][1]
            if raw:
                out.append((uid, raw))
        return out
    finally:
        try:
            imap.logout()
        except Exception:
            pass

def parse_rfc822(raw: bytes) -> dict:
    m: Message = email.message_from_bytes(raw)
    def _getall(name: str) -> list[str]:
        vals = m.get_all(name) or []
        return [str(v) for v in vals]

    subject = str(m.get("Subject") or "")
    from_email = str(m.get("From") or "")
    to_email = str(m.get("To") or "")
    cc_email = str(m.get("Cc") or "")
    msg_id = str(m.get("Message-ID") or "")
    in_reply_to = str(m.get("In-Reply-To") or "") or None
    references = _getall("References")
    x_erp = str(m.get("X-ERP-MSG") or "") or None

    body_text = ""
    body_html = ""
    attachments: list[dict] = []

    if m.is_multipart():
        for part in m.walk():
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True) or b""
                body_text += payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            elif ctype == "text/html" and "attachment" not in disp:
                payload = part.get_payload(decode=True) or b""
                body_html += payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            elif "attachment" in disp:
                filename = part.get_filename() or "attachment"
                payload = part.get_payload(decode=True) or b""
                attachments.append({
                    "filename": filename,
                    "content_type": ctype,
                    "content": payload,
                })
    else:
        ctype = m.get_content_type()
        payload = m.get_payload(decode=True) or b""
        if ctype == "text/html":
            body_html = payload.decode(m.get_content_charset() or "utf-8", errors="replace")
        else:
            body_text = payload.decode(m.get_content_charset() or "utf-8", errors="replace")

    return {
        "subject": subject,
        "from_email": from_email,
        "to_raw": to_email,
        "cc_raw": cc_email,
        "smtp_message_id": msg_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "x_erp_msg": x_erp,
        "body_text": body_text,
        "body_html": body_html,
        "attachments": attachments,
    }
