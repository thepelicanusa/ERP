from __future__ import annotations

import smtplib
from email.message import EmailMessage as PyEmailMessage
from email.utils import make_msgid, formatdate
from typing import Iterable, Optional, Tuple


def _inject_open_pixel(body_html: str, tracking_pixel_url: str) -> str:
    """Best-effort open tracking.

    We append a 1x1 pixel at the end of the HTML body. Email clients that block
    remote images won't trigger opens.
    """
    if not body_html:
        return body_html
    if tracking_pixel_url in body_html:
        return body_html
    pixel = f'<img src="{tracking_pixel_url}" width="1" height="1" style="display:none" alt="" />'
    # If there's a closing body tag, inject before it; otherwise append.
    lower = body_html.lower()
    idx = lower.rfind("</body>")
    if idx != -1:
        return body_html[:idx] + pixel + body_html[idx:]
    return body_html + pixel


def _rewrite_links_for_click_tracking(body_html: str, click_base_url: str, msg_uuid: str) -> str:
    """Very small, safe-ish link rewriter.

    Rewrites href="https://..." into href="{click_base_url}/{msg_uuid}/{n}?u=...".
    This is intentionally simple (regex-based) to keep dependencies light.
    """
    if not body_html:
        return body_html
    import re
    import urllib.parse

    # Only rewrite http/https links.
    href_re = re.compile(r'href=[\"\'](https?://[^\"\']+)[\"\']', re.IGNORECASE)
    counter = {"i": 0}

    def _sub(m: re.Match) -> str:
        counter["i"] += 1
        dest = m.group(1)
        u = urllib.parse.quote(dest, safe="")
        tracked = f"{click_base_url}/{msg_uuid}/{counter['i']}?u={u}"
        return f'href="{tracked}"'

    return href_re.sub(_sub, body_html)

def build_message(
    *,
    from_email: str,
    to_emails: list[str],
    subject: str,
    body_text: str = "",
    body_html: str = "",
    cc_emails: Optional[list[str]] = None,
    bcc_emails: Optional[list[str]] = None,
    correlation_token: Optional[str] = None,
    tracking_open_url: Optional[str] = None,
    tracking_click_base_url: Optional[str] = None,
    msg_uuid: Optional[str] = None,
    attachments: Optional[list[Tuple[str, bytes, str]]] = None,  # (filename, content, mimetype)
) -> PyEmailMessage:
    msg = PyEmailMessage()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=None)

    if correlation_token:
        # Helps routing even when email headers are mangled
        msg["X-ERP-MSG"] = correlation_token

    if body_html:
        # Tracking (best-effort)
        if tracking_click_base_url and msg_uuid:
            body_html = _rewrite_links_for_click_tracking(body_html, tracking_click_base_url, msg_uuid)
        if tracking_open_url:
            body_html = _inject_open_pixel(body_html, tracking_open_url)
        msg.set_content(body_text or " ")
        msg.add_alternative(body_html, subtype="html")
    else:
        msg.set_content(body_text or " ")

    for (filename, content, mimetype) in (attachments or []):
        maintype, subtype = (mimetype.split("/", 1) + ["octet-stream"])[:2]
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

    return msg

def send_smtp(
    *,
    host: str,
    port: int,
    use_tls: bool,
    username: str,
    password: str,
    msg: PyEmailMessage,
    envelope_from: Optional[str] = None,
    envelope_to: Optional[Iterable[str]] = None,
) -> None:
    envelope_from = envelope_from or msg.get("From")
    tos: list[str] = []
    if envelope_to:
        tos = list(envelope_to)
    else:
        for hdr in ("To", "Cc", "Bcc"):
            v = msg.get(hdr)
            if v:
                tos.extend([x.strip() for x in v.split(",") if x.strip()])
    # Ensure Bcc header not sent
    if msg.get("Bcc"):
        del msg["Bcc"]

    if use_tls:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            if username:
                s.login(username, password)
            s.send_message(msg, from_addr=envelope_from, to_addrs=tos)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            if username:
                s.login(username, password)
            s.send_message(msg, from_addr=envelope_from, to_addrs=tos)
