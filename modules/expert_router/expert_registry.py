"""Expert registry and heuristic routing helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List


EXPERTS = [
    "risk",
    "risk_resources",
    "grand_strategist",
    "strategy",
    "intelligence",
    "timing",
    "technology",
    "optionality",
    "data",
    "diplomacy",
    "psychology",
    "legitimacy",
    "conflict",
    "truth",
    "discipline",
    "power",
    "narrative",
    "sovereign",
    "adaptation",
    "war_mode",
]

_DOMAIN_EXPERT_MAP = {
    "strategy": ["grand_strategist", "intelligence", "timing", "power"],
    "risk": ["risk", "risk_resources", "legitimacy"],
    "ethics": ["legitimacy", "truth", "discipline"],
    "resource_allocation": ["data", "optionality", "risk_resources"],
    "long_term_tradeoffs": ["grand_strategist", "optionality", "timing"],
    "innovation": ["technology", "grand_strategist", "risk"],
    "power": ["power", "diplomacy", "conflict"],
    "relationships": ["diplomacy", "psychology", "legitimacy"],
    "financial": ["risk", "optionality", "data"],
}


def expert_weights_from_context(prompt: str, context: Dict[str, Any]) -> Dict[str, float]:
    domains = [str(item).strip().lower() for item in (context.get("domains") or [])]
    weights = defaultdict(float)
    for domain in domains:
        for expert in _DOMAIN_EXPERT_MAP.get(domain, []):
            weights[expert] += 1.0

    # Keyword-based fallback if domains absent.
    if not weights:
        text = f"{prompt} {context}".lower()
        if "risk" in text or "compliance" in text or "exposure" in text:
            weights["risk"] += 1.5
            weights["legitimacy"] += 0.5
        if "strategy" in text or "competitor" in text or "market" in text:
            weights["grand_strategist"] += 1.0
            weights["intelligence"] += 0.5
        if "ethic" in text or "privacy" in text or "bias" in text:
            weights["legitimacy"] += 1.0
            weights["truth"] += 0.5
        if "budget" in text or "allocation" in text:
            weights["data"] += 1.0
            weights["optionality"] += 0.5

    if not weights:
        weights["risk"] = 1.0

    total = sum(weights.values()) or 1.0
    return {expert: value / total for expert, value in weights.items()}


def normalize_experts(experts: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    seen = set()
    for item in experts:
        text = str(item).strip().lower()
        if text and text in EXPERTS and text not in seen:
            normalized.append(text)
            seen.add(text)
    return normalized
