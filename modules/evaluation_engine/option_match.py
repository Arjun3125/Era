"""Option matching utilities for evaluation."""

from __future__ import annotations

import re
from typing import Iterable


def normalize_option(text: str) -> str:
    value = str(text or "").strip().lower()
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def match_option(predicted: str, options: Iterable[str]) -> str:
    normalized = normalize_option(predicted)
    if not normalized:
        return ""
    option_list = [str(item) for item in options]
    normalized_options = [normalize_option(item) for item in option_list]
    if normalized in normalized_options:
        return option_list[normalized_options.index(normalized)]

    # Substring match.
    for original, candidate in zip(option_list, normalized_options):
        if normalized and normalized in candidate:
            return original
    # Token overlap.
    pred_tokens = set(normalized.split())
    best = (0, "")
    for original, candidate in zip(option_list, normalized_options):
        tokens = set(candidate.split())
        overlap = len(pred_tokens & tokens)
        if overlap > best[0]:
            best = (overlap, original)
    return best[1]
