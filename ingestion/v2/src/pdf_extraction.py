"""PDF extraction helpers for v2 ingestion (compat shim)."""
from __future__ import annotations

from typing import List

from ingestion.v1.ingest import extract_pdf_pages as _extract_pdf_pages


def extract_pdf_pages(pdf_path: str, **kwargs) -> List[str]:
    """Reuse v1 stub extraction for tests."""
    return _extract_pdf_pages(pdf_path, **kwargs)


def looks_glyph_encoded(text: str) -> bool:
    """Basic heuristic: detect high ratio of non-ascii glyphs."""
    if not text:
        return False
    total = len(text)
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    return (non_ascii / max(1, total)) > 0.15


def repair_glyph_text(text: str) -> str:
    """Placeholder glyph repair: no-op for test harness."""
    return text
