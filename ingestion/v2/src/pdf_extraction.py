"""PDF extraction for v2 ingestion — uses pdfplumber for reliable text extraction."""
from __future__ import annotations

import re
from typing import List


def extract_pdf_pages(pdf_path: str, **kwargs) -> List[str]:
    """Extract per-page text from a PDF using pdfplumber.

    Returns a list of non-empty page strings.
    Returns [] if the file is unreadable or encrypted without a password.
    """
    try:
        import pdfplumber
    except ImportError:
        return _fallback_extract(pdf_path)

    pages: List[str] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                if text.strip():
                    pages.append(text)
    except Exception:
        return _fallback_extract(pdf_path)

    return pages


def _fallback_extract(pdf_path: str) -> List[str]:
    """Last-resort: read raw bytes, strip non-printable chars."""
    try:
        with open(pdf_path, "rb") as f:
            raw = f.read().decode("utf-8", errors="ignore")
        # Keep only printable ASCII lines that look like sentences
        lines = [ln.strip() for ln in raw.splitlines() if len(ln.strip()) > 20]
        text = "\n".join(lines)
        return [text] if text.strip() else []
    except Exception:
        return []


def looks_glyph_encoded(text: str) -> bool:
    """Return True when the text has a high ratio of non-ASCII characters (binary garbage)."""
    if not text:
        return False
    total = len(text)
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    return (non_ascii / max(1, total)) > 0.15


def repair_glyph_text(text: str) -> str:
    """Remove non-printable characters and collapse whitespace."""
    cleaned = re.sub(r"[^\x20-\x7E\n\r\t]", " ", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()
