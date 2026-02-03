from __future__ import annotations

from typing import Optional


def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Best-effort PDF text extraction.

    Works well for text-based PDFs. For scanned PDFs, you'll want OCR in Phase 2.
    """
    if not data:
        return ""
    try:
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(data))
        chunks: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t:
                chunks.append(t)
        return "\n".join(chunks)
    except Exception:
        return ""
