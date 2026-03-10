"""Knowledge feature extraction for learning models."""

from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

TOKEN_RE = re.compile(r"[a-z][a-z0-9_]+")


def _tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


@lru_cache(maxsize=1)
def _load_principles() -> List[Dict[str, Any]]:
    for path in (Path("knowledge/principles.json"), Path("data/principles.json")):
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return []


def build_knowledge_features(prompt: str) -> Dict[str, float]:
    principles = _load_principles()
    if not principles or not prompt:
        return {"knowledge_match_count": 0.0, "knowledge_avg_success_rate": 0.0}

    prompt_tokens = set(_tokenize(prompt))
    matched = []
    for item in principles:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        text_tokens = set(_tokenize(text))
        if prompt_tokens & text_tokens:
            matched.append(item)

    domains = Counter(str(item.get("domain", "unknown")) for item in matched)
    features: Dict[str, float] = {
        "knowledge_match_count": float(len(matched)),
        "knowledge_avg_success_rate": float(
            sum(float(item.get("historical_success_rate", 0.5)) for item in matched) / len(matched)
        )
        if matched
        else 0.0,
    }
    for domain, count in domains.items():
        features[f"knowledge_domain_{domain}"] = float(count)
    return features


def augment_context_with_knowledge(context: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    merged = dict(context or {})
    merged.update(build_knowledge_features(prompt))
    return merged
