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
        lines.append(f"brier_score: {block.get('brier_score', 0.0):.4f}")
        lines.append(f"avg_regret: {block.get('avg_regret', 0.0):.4f}")
        lines.append(f"rubric_score: {block.get('rubric_score', 0.0):.4f}")
        if "avg_risk_score" in block:
            lines.append(f"avg_risk_score: {block.get('avg_risk_score', 0.0):.4f}")
        lines.append("")

    section("ERA", era)
    if simulator:
        lines.append("Simulator:")
        lines.append(f"accuracy: {simulator.get('accuracy', 0.0):.4f}")
        lines.append("")
    if baseline:
        section("Baseline", baseline)

    budget_dist = summary.get("budget_distribution") or {}
    if budget_dist:
        lines.append("Budget distribution")
        for key in sorted(budget_dist.keys(), key=lambda k: int(k)):
            lines.append(f"  {key}: {budget_dist[key]}")
        lines.append(f"avg_budget: {summary.get('avg_budget', 0.0):.4f}")
        lines.append("")

    budget_efficiency = summary.get("budget_efficiency") or {}
    overall_eff = budget_efficiency.get("overall") or {}
    if overall_eff:
        lines.append("Budget efficiency")
        lines.append(f"avg_quality: {overall_eff.get('avg_quality', 0.0):.4f}")
        lines.append(f"avg_compute_cost: {overall_eff.get('avg_compute_cost', 0.0):.4f}")
        lines.append(f"avg_efficiency: {overall_eff.get('avg_efficiency', 0.0):.4f}")
        lines.append("")

    per_budget = budget_efficiency.get("by_budget") or {}
    if per_budget:
        lines.append("Budget efficiency by budget")
        for budget in sorted(per_budget.keys(), key=lambda k: int(k)):
            item = per_budget[budget]
            lines.append(
                f"  {budget}: "
                f"quality={item.get('avg_quality', 0.0):.4f}, "
                f"cost={item.get('avg_compute_cost', 0.0):.4f}, "
                f"eff={item.get('avg_efficiency', 0.0):.4f}"
            )
        lines.append("")

    lines.append("Category scores")
    for cat, score in summary.get("category_scores", {}).items():
        lines.append(f"  {cat}: {score:.4f}")

    return "\n".join(lines)
