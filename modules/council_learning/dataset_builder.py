"""Dataset builder for council weight learning (bootstrap targets)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from modules.learning_core import augment_context_with_knowledge
from modules.expert_router.expert_registry import EXPERTS, expert_weights_from_context


_STANCE_SCORE = {
    "support": 1.0,
    "neutral": 0.5,
    "oppose": 0.0,
}


@dataclass
class DatasetRow:
    scenario_id: str
    prompt: str
    context: Dict[str, Any]
    experts: List[str]
    weights: List[float]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "prompt": self.prompt,
            "context": self.context,
            "experts": self.experts,
            "weights": self.weights,
        }


def load_scenarios(root: Path) -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = []
    for category_dir in sorted((root / "scenarios").iterdir()):
        if not category_dir.is_dir():
            continue
        for path in sorted(category_dir.glob("*.json")):
            scenarios.append(json.loads(path.read_text(encoding="utf-8")))
    return scenarios


def load_simulated_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _group_simulated_rows(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for idx, row in enumerate(rows):
        sample_id = row.get("sample_id")
        if sample_id:
            key = f"sample:{sample_id}"
        elif "scenario_instance" in row:
            key = f"instance:{row.get('scenario_instance')}"
        else:
            prompt = row.get("prompt", "")
            context = row.get("context", {})
            context_key = json.dumps(context, sort_keys=True)
            key = f"scenario:{row.get('scenario_id')}|{prompt}|{context_key}|{idx // 4}"
        grouped.setdefault(key, []).append(row)
    return grouped


def build_dataset_from_simulated(
    *,
    simulated_path: Path,
    output_path: Path,
) -> List[DatasetRow]:
    rows = load_simulated_rows(simulated_path)
    grouped = _group_simulated_rows(rows)
    dataset_rows: List[DatasetRow] = []

    for group_rows in grouped.values():
        anchor = group_rows[0]
        prompt = anchor.get("prompt", "")
        context = augment_context_with_knowledge(anchor.get("context", {}), prompt)
        weights_map = expert_weights_from_context(prompt, context)
        weights = [float(weights_map.get(expert, 0.0)) for expert in EXPERTS]
        dataset_rows.append(
            DatasetRow(
                scenario_id=anchor.get("scenario_id", "") or anchor.get("sample_id", ""),
                prompt=prompt,
                context=context,
                experts=list(EXPERTS),
                weights=weights,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in dataset_rows:
            handle.write(json.dumps(row.as_dict(), ensure_ascii=True))
            handle.write("\n")
    return dataset_rows


def build_dataset(
    *,
    scenarios_root: Path,
    output_path: Path,
) -> List[DatasetRow]:
    scenarios = load_scenarios(scenarios_root)
    rows: List[DatasetRow] = []

    for scenario in scenarios:
        prompt = scenario.get("prompt", "")
        context = augment_context_with_knowledge(scenario.get("context", {}), prompt)
        weights_map = expert_weights_from_context(prompt, context)
        weights = [float(weights_map.get(expert, 0.0)) for expert in EXPERTS]
        rows.append(
            DatasetRow(
                scenario_id=scenario.get("scenario_id", ""),
                prompt=prompt,
                context=context,
                experts=list(EXPERTS),
                weights=weights,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.as_dict(), ensure_ascii=True))
            handle.write("\n")
    return rows


def build_dataset_from_runs(
    *,
    runs_path: Path,
    output_path: Path,
) -> List[DatasetRow]:
    rows: List[DatasetRow] = []
    if not runs_path.exists():
        raise FileNotFoundError(f"Runs file not found: {runs_path}")

    with runs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            minister_outputs = payload.get("minister_outputs") or {}
            if not isinstance(minister_outputs, dict):
                continue
            weights: List[float] = []
            for expert in EXPERTS:
                details = minister_outputs.get(expert, {})
                if not isinstance(details, dict):
                    details = {}
                stance = str(details.get("stance", "neutral")).strip().lower()
                confidence = details.get("confidence", 0.0) or 0.0
                try:
                    confidence = float(confidence)
                except Exception:
                    confidence = 0.0
                confidence = max(0.0, min(1.0, confidence))
                base = _STANCE_SCORE.get(stance, 0.0)
                weights.append(round(base * confidence, 4))

            prompt = payload.get("prompt", "")
            context = augment_context_with_knowledge(payload.get("context", {}), prompt)
            rows.append(
                DatasetRow(
                    scenario_id=payload.get("scenario_id", ""),
                    prompt=prompt,
                    context=context,
                    experts=list(EXPERTS),
                    weights=weights,
                )
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.as_dict(), ensure_ascii=True))
            handle.write("\n")
    return rows
