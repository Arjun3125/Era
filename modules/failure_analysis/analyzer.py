"""Analyze failure traces from benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping

from .clustering import cluster_failures
from .error_categories import FailureCategoryConfig, classify_failure


@dataclass
class FailureAnalysis:
    total: int
    failures: int
    failure_rate: float
    category_accuracy: Dict[str, float]
    failure_type_counts: Dict[str, int]
    worst_categories: List[str]
    top_failures: List[Dict[str, Any]]
    clusters: List[Dict[str, Any]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "failures": self.failures,
            "failure_rate": self.failure_rate,
            "category_accuracy": self.category_accuracy,
            "failure_type_counts": self.failure_type_counts,
            "worst_categories": list(self.worst_categories),
            "top_failures": list(self.top_failures),
            "clusters": list(self.clusters),
        }


def analyze_traces(
    traces: Iterable[Mapping[str, Any]],
    *,
    config: FailureCategoryConfig | None = None,
    top_k: int = 20,
    cluster_count: int = 0,
    cluster_min_size: int = 2,
    cluster_top_terms: int = 5,
) -> FailureAnalysis:
    items = list(traces)
    failures = [trace for trace in items if _is_failure(trace)]

    failure_type_counts: Dict[str, int] = {}
    for trace in failures:
        categories = classify_failure(trace, config)
        for category in categories:
            failure_type_counts[category] = failure_type_counts.get(category, 0) + 1

    category_accuracy = _category_accuracy(items)
    worst_categories = [
        cat
        for cat, _ in sorted(category_accuracy.items(), key=lambda item: item[1])[:5]
    ]
    top_failures = sorted(failures, key=lambda trace: float(trace.get("regret", 0.0)), reverse=True)[:top_k]
    total = len(items)
    failure_count = len(failures)
    failure_rate = (failure_count / total) if total else 0.0
    clusters: List[Dict[str, Any]] = []
    if cluster_count > 0 and failures:
        clusters = cluster_failures(
            failures,
            max_clusters=cluster_count,
            min_cluster_size=cluster_min_size,
            top_terms=cluster_top_terms,
        )

    return FailureAnalysis(
        total=total,
        failures=failure_count,
        failure_rate=round(failure_rate, 4),
        category_accuracy=category_accuracy,
        failure_type_counts=failure_type_counts,
        worst_categories=worst_categories,
        top_failures=top_failures,
        clusters=clusters,
    )


def _is_failure(trace: Mapping[str, Any]) -> bool:
    decision = str(trace.get("model_decision", "")).strip().lower()
    expected = str(trace.get("expected_decision", "")).strip().lower()
    return decision != expected and expected != ""


def _category_accuracy(traces: Iterable[Mapping[str, Any]]) -> Dict[str, float]:
    grouped: Dict[str, List[int]] = {}
    for trace in traces:
        category = str(trace.get("category", "unknown"))
        correct = int(bool(trace.get("decision_correct", 0)))
        grouped.setdefault(category, []).append(correct)
    accuracy: Dict[str, float] = {}
    for category, values in grouped.items():
        accuracy[category] = round(sum(values) / len(values), 4) if values else 0.0
    return dict(sorted(accuracy.items()))
