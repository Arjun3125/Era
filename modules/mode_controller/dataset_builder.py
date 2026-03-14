"""Dataset builder for adaptive mode controller training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from modules.learning_core import augment_context_with_knowledge


_LEVEL_SCORES = {"low": 0.2, "medium": 0.5, "high": 0.8}


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
            grouped.setdefault(scenario_id, {}).setdefault(budget, []).append(score)
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
        context = meta.get(scenario_id, {}).get("context", {}) or {}
        signals = meta.get(scenario_id, {}).get("signals", {}) or {}

        enriched = dict(context)
        _inject_numeric_features(enriched, signals)
        enriched = augment_context_with_knowledge(enriched, prompt)

        rows.append(
            DatasetRow(
                scenario_id=scenario_id,
                prompt=prompt,
                context=enriched,
                budget=int(best_budget),
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.as_dict(), ensure_ascii=True))
            handle.write("\n")
    return rows


def _inject_numeric_features(context: Dict[str, Any], signals: Dict[str, Any]) -> None:
    stake = _LEVEL_SCORES.get(str(context.get("stake_level", "")).lower(), 0.0)
    reversibility = _LEVEL_SCORES.get(str(context.get("reversibility", "")).lower(), 0.0)
    regulatory = _LEVEL_SCORES.get(str(context.get("regulatory_pressure", "")).lower(), 0.0)

    risk_score = 0.0
    risk_score += stake
    risk_score += 0.5 * regulatory
    risk_score += 0.5 * (1.0 - reversibility)
    risk_score = max(0.0, min(1.0, risk_score))

    context["risk_score"] = round(risk_score, 4)
    context["stake_level_score"] = round(stake, 4)
    context["reversibility_score"] = round(reversibility, 4)

    _set_numeric(context, "decision_horizon_months", 0.0)
    _set_numeric(context, "time_pressure_days", 0.0)

    if isinstance(signals, dict):
        context["policy_entropy"] = _safe_float(signals.get("policy_entropy", 0.0))
        context["value_variance"] = _safe_float(signals.get("value_variance", 0.0))
        context["minister_disagreement"] = _safe_float(signals.get("minister_disagreement", 0.0))


def _set_numeric(context: Dict[str, Any], key: str, default: float) -> None:
    context[key] = _safe_float(context.get(key, default))


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
