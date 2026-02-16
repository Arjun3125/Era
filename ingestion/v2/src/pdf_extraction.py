"""PDF extraction helpers for v2."""
from typing import List, Optional
from pypdf import PdfReader
import unicodedata
import os
import logging

# Suppress pypdf warnings about "Odd-length string" and other internal errors
# These are non-fatal decoding issues that don't affect extraction quality
logging.getLogger("pypdf").setLevel(logging.CRITICAL)
logging.getLogger("pypdf._page").setLevel(logging.CRITICAL)


def extract_pdf_pages(pdf_path: str, storage: Optional[str] = None) -> List[str]:
    reader = PdfReader(pdf_path)
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    return pages


def looks_glyph_encoded(text: str, *, threshold: float = 0.08) -> bool:
    """Heuristic to detect glyph/font-encoding artifacts in extracted text."""
    if not text:
        return False
    total = len(text)
    if total == 0:
        return False
    non_ascii = sum(1 for c in text if ord(c) > 127)
    non_ascii_ratio = non_ascii / max(total, 1)

    weird = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("C") or cat.startswith("S"):
            weird += 1
    weird_ratio = weird / max(total, 1)

    return (non_ascii_ratio > 0.15 and weird_ratio > 0.05) or (weird_ratio > 0.12)


def repair_glyph_text(text: str, *, client: Optional[object] = None, storage: Optional[str] = None) -> str:
    """Attempt a glyph repair using the provided LLM client; fallback to original text.

    The function is intentionally conservative: if the client is unavailable or
    the call fails, return the original text unchanged.
    """
    if not client or not hasattr(client, "generate"):
        return text

    prompt = f"""
The following text contains font-encoding or glyph artifacts.
Repair it into clean, readable English.
Do not summarize or omit content.

TEXT:
{text[:12000]}
"""
    try:
        repaired = client.generate(prompt).strip()
        if repaired:
            # persist to cache if storage provided
            try:
                key = str(abs(hash(text)))
                cache_path = os.path.join(storage or ".", f"glyph_repair_{key}.txt")
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(repaired)
            except Exception:
                pass
            return repaired
    except Exception:
        pass

    return text
