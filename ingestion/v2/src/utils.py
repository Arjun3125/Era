"""Utility functions for text processing, hashing, and validation."""
import hashlib
import json
import re
import unicodedata
from typing import Any, Dict, List


def sha(text: str) -> str:
    """Generate SHA-256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(text: str, *, max_chars: int = 8000) -> List[str]:
    """
    Split text into chunks at paragraph boundaries.
    
    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk
        
    Returns:
        List of text chunks
    """
    out: List[str] = []
    n = len(text)
    start = 0
    while start < n:
        end = min(start + max_chars, n)
        cut = text.rfind("\n\n", start, end)
        if cut == -1 or cut <= start:
            cut = end
        out.append(text[start:cut])
        start = cut

    return [c for c in out if c.strip()]


def dedupe_list(items: List[Any]) -> List[Any]:
    """
    Deterministically deduplicate a list while preserving order.
    Handles both strings and dicts.
    
    Args:
        items: List to deduplicate
        
    Returns:
        Deduplicated list
    """
    seen = set()
    out = []

    for item in items:
        key = (
            json.dumps(item, sort_keys=True, ensure_ascii=False)
            if isinstance(item, dict)
            else str(item)
        )
        if key not in seen:
            seen.add(key)
            out.append(item)

    return out


def looks_glyph_encoded(text: str, *, threshold: float = 0.08) -> bool:
    """
    Detect font-encoding or glyph artifacts in text.
    Uses non-ASCII density and unicode category signals.
    
    Args:
        text: Text to analyze
        threshold: Detection threshold (unused, kept for API compatibility)
        
    Returns:
        True if text appears to have glyph artifacts
    """
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

    # require both high non-ascii ratio and substantial weird char ratio
    return (non_ascii_ratio > 0.15 and weird_ratio > 0.05) or (weird_ratio > 0.12)


def text_quality_score(text: str) -> float:
    """
    Score text quality based on printable character ratio.
    
    Args:
        text: Text to score
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    if not text:
        return 0.0
    printable = sum(1 for c in text if c.isprintable())
    return printable / max(len(text), 1)


def is_glyph_stream(text: str) -> bool:
    """
    Detect glyph stream markers in text.
    
    Args:
        text: Text to check
        
    Returns:
        True if glyph stream markers detected
    """
    return bool(re.search(r'/G[0-9A-Fa-f]{2}', text))


def infer_domains_from_text(text: str, max_domains: int = 3) -> List[str]:
    """
    Infer applicable doctrine domains from text keywords.
    
    Args:
        text: Text to analyze
        max_domains: Maximum number of domains to return
        
    Returns:
        List of inferred domains
    """
    from .config import DOMAIN_KEYWORDS
    
    lc = (text or "").lower()
    scores = {}
    for d, kws in DOMAIN_KEYWORDS.items():
        s = 0
        for kw in kws:
            s += lc.count(kw)
        if s > 0:
            scores[d] = s
    if not scores:
        return ["strategy"]
    # sort by score desc and return top N
    ordered = sorted(scores.items(), key=lambda x: -x[1])
    return [d for d, _ in ordered[:max_domains]]