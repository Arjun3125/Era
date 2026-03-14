"""Dataset builder for expert router learning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from modules.learning_core import augment_context_with_knowledge
from .expert_registry import EXPERTS, expert_weights_from_context


@dataclass
class DatasetRow:
    scenario_id: str
    prompt: str
    context: Dict[str, Any]
    experts: List[str]
    weights: List[float]
    labels: List[int]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "prompt": self.prompt,
            "context": self.context,
            "experts": self.experts,
            "weights": self.weights,
            "labels": self.labels,
        }


def load_scenarios(root: Path) -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = []
    for category_dir in sorted((root / "scenarios").iterdir()):
        if not category_dir.is_dir():
            continue
        for path in sorted(category_dir.glob("*.json")):
            scenarios.append(json.loads(path.read_text(encoding="utf-8")))
    return scenarios


def build_dataset(
    *,
    scenarios_root: Path,
    output_path: Path,
    label_threshold: float = 0.15,
) -> List[DatasetRow]:
    scenarios = load_scenarios(scenarios_root)
    rows: List[DatasetRow] = []

    for scenario in scenarios:
        prompt = scenario.get("prompt", "")
        base_context = augment_context_with_knowledge(scenario.get("context", {}), prompt)
        category = str(scenario.get("category", "")).strip().lower()
        if category:
            base_context = dict(base_context)
            base_context.setdefault("domains", [category])
        weights_map = expert_weights_from_context(prompt, base_context)
        weights = [float(weights_map.get(expert, 0.0)) for expert in EXPERTS]
        labels = [1 if value >= label_threshold else 0 for value in weights]
        rows.append(
            DatasetRow(
                scenario_id=scenario.get("scenario_id", ""),
                prompt=prompt,
                context=base_context,
                experts=list(EXPERTS),
                weights=weights,
                labels=labels,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.as_dict(), ensure_ascii=True))
            handle.write("\n")
    return rows
