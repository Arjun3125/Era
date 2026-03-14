"""Dataset builder for reasoning controller training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from modules.learning_core import augment_context_with_knowledge


@dataclass
class DatasetRow:
    scenario_id: str
    prompt: str
    context: Dict[str, Any]
    budget: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "prompt": self.prompt,
            "context": self.context,
            "budget": self.budget,
        }


def build_dataset_from_runs(
    *,
    runs_path: Path,
    output_path: Path,
) -> List[DatasetRow]:
    if not runs_path.exists():
        raise FileNotFoundError(f"Runs file not found: {runs_path}")

    grouped: Dict[str, Dict[int, List[float]]] = {}
    meta: Dict[str, Dict[str, Any]] = {}

    with runs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            scenario_id = str(payload.get("scenario_id", "")).strip()
            if not scenario_id:
                continue
            budget = int(payload.get("budget", 0))
            score = float(payload.get("score", 0.0))
            utility = payload.get("utility")
            if utility is None and "quality" in payload and "compute_cost" in payload:
                try:
                    utility = float(payload.get("quality", 0.0)) - float(payload.get("compute_cost", 0.0))
                except (TypeError, ValueError):
                    utility = None
            if utility is None:
                utility = score
            grouped.setdefault(scenario_id, {}).setdefault(budget, []).append(float(utility))
            if scenario_id not in meta:
                meta[scenario_id] = {
                    "prompt": payload.get("prompt", ""),
                    "context": payload.get("context", {}),
                    "signals": payload.get("signals", {}),
                }

    rows: List[DatasetRow] = []
    for scenario_id, budgets in grouped.items():
        if not budgets:
            continue
        best_budget = None
        best_score = None
        for budget, scores in budgets.items():
            if not scores:
                continue
            avg = sum(scores) / len(scores)
            if best_score is None or avg > best_score:
                best_score = avg
                best_budget = budget
        if best_budget is None:
            continue
        prompt = meta.get(scenario_id, {}).get("prompt", "")
        context = meta.get(scenario_id, {}).get("context", {})
        signals = meta.get(scenario_id, {}).get("signals", {}) or {}
        if isinstance(signals, dict):
            for key in ("policy_entropy", "value_variance", "minister_disagreement", "risk_score"):
                if key in signals:
                    context[key] = signals[key]
        context = augment_context_with_knowledge(context, prompt)
        rows.append(
            DatasetRow(
                scenario_id=scenario_id,
                prompt=prompt,
                context=context,
                budget=int(best_budget),
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.as_dict(), ensure_ascii=True))
            handle.write("\n")
    return rows
