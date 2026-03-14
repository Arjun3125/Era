"""Dataset builder for policy model training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from modules.evaluation_engine.option_match import match_option
from modules.learning_core import augment_context_with_knowledge


@dataclass
class DatasetRow:
    scenario_id: str
    category: str
    prompt: str
    option: str
    context: Dict[str, Any]
    expected_decision: str
    label: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "category": self.category,
            "prompt": self.prompt,
            "option": self.option,
            "context": self.context,
            "expected_decision": self.expected_decision,
            "label": self.label,
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
        best_option = ""
        best_reward = None
        for row in group_rows:
            reward = float(row.get("reward", 0.0))
            if best_reward is None or reward > best_reward:
                best_reward = reward
                best_option = str(row.get("option", ""))

        for row in group_rows:
            prompt = row.get("prompt", "")
            context = augment_context_with_knowledge(row.get("context", {}), prompt)
            option = str(row.get("option", ""))
            label = 1 if option == best_option else 0
            dataset_rows.append(
                DatasetRow(
                    scenario_id=row.get("scenario_id", "") or row.get("sample_id", ""),
                    category=row.get("category", ""),
                    prompt=prompt,
                    option=option,
                    context=context,
                    expected_decision=best_option,
                    label=label,
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
        base_context = augment_context_with_knowledge(scenario.get("context", {}), prompt)
        options = scenario.get("decision_options", [])
        expected = scenario.get("expected_decision", "")
        for option in options:
            normalized_option = match_option(option, options) or str(option)
            label = 1 if normalized_option == expected else 0
            rows.append(
                DatasetRow(
                    scenario_id=scenario.get("scenario_id", ""),
                    category=scenario.get("category", ""),
                    prompt=prompt,
                    option=str(option),
                    context=base_context,
                    expected_decision=expected,
                    label=label,
                )
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.as_dict(), ensure_ascii=True))
            handle.write("\n")
    return rows
