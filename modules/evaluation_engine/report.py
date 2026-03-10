"""Aggregate reporting for ERA evaluation runs."""

from __future__ import annotations

from typing import Dict, Iterable

from .metrics import average


def generate_report(summary: Dict[str, any]) -> str:
    lines = ["ERA Benchmark Report"]
    lines.append(f"Scenarios tested: {summary.get('scenario_count', 0)}")
    lines.append("")

    era = summary.get("era", {})
    baseline = summary.get("baseline", {})
    simulator = summary.get("simulator", {})

    def section(title: str, block: Dict[str, any]) -> None:
        lines.append(f"{title}:")
        lines.append(f"accuracy: {block.get('accuracy', 0.0):.4f}")
        lines.append(f"ECE: {block.get('ece', 0.0):.4f}")
        lines.append(f"avg_regret: {block.get('avg_regret', 0.0):.4f}")
        lines.append(f"rubric_score: {block.get('rubric_score', 0.0):.4f}")
        lines.append("")

    section("ERA", era)
    if simulator:
        lines.append("Simulator:")
        lines.append(f"accuracy: {simulator.get('accuracy', 0.0):.4f}")
        lines.append("")
    if baseline:
        section("Baseline", baseline)

    lines.append("Category scores")
    for cat, score in summary.get("category_scores", {}).items():
        lines.append(f"  {cat}: {score:.4f}")

    return "\n".join(lines)
