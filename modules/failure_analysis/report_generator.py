"""Generate human-readable failure analysis reports."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .analyzer import FailureAnalysis


def generate_report(analysis: FailureAnalysis) -> str:
    lines = ["ERA Failure Analysis"]
    lines.append(f"Total scenarios: {analysis.total}")
    lines.append(f"Failures: {analysis.failures}")
    lines.append(f"Failure rate: {analysis.failure_rate:.4f}")
    lines.append("")

    lines.append("Failure distribution:")
    for name, count in sorted(analysis.failure_type_counts.items(), key=lambda item: item[1], reverse=True):
        pct = (count / analysis.failures) * 100 if analysis.failures else 0.0
        lines.append(f"  {name}: {count} ({pct:.1f}%)")
    lines.append("")

    lines.append("Worst categories:")
    for category in analysis.worst_categories:
        lines.append(f"  {category}: {analysis.category_accuracy.get(category, 0.0):.4f}")
    lines.append("")

    lines.append("Top regret failures:")
    for trace in analysis.top_failures:
        lines.append(
            f"  {trace.get('scenario_id')} | "
            f"category={trace.get('category')} | "
            f"regret={trace.get('regret', 0.0):.4f} | "
            f"decision={trace.get('model_decision')} | expected={trace.get('expected_decision')}"
        )
    lines.append("")

    if analysis.clusters:
        lines.append("Failure clusters:")
        for cluster in analysis.clusters:
            terms = ", ".join(cluster.get("top_terms", []))
            examples = ", ".join(cluster.get("example_ids", []))
            lines.append(
                f"  cluster {cluster.get('cluster_id')} "
                f"(size={cluster.get('size')}): {terms}"
            )
            if examples:
                lines.append(f"    examples: {examples}")
        lines.append("")

    return "\n".join(lines)


def write_report(path: Path, analysis: FailureAnalysis) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_report(analysis), encoding="utf-8")
