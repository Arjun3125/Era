"""PDF extraction helpers for v2 ingestion (compat shim)."""
from __future__ import annotations

from typing import List

import logging
import pdfplumber

logger = logging.getLogger(__name__)

def extract_pdf_pages(pdf_path: str, **kwargs) -> List[str]:
    """Extract real text from a PDF file using pdfplumber."""
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
            else:
                pages_text.append("")
    return pages_text


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
