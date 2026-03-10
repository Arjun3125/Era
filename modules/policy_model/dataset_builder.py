"""Dataset builder for policy model training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from modules.evaluation_engine.option_match import match_option


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


def build_dataset(
    *,
    scenarios_root: Path,
    output_path: Path,
) -> List[DatasetRow]:
    scenarios = load_scenarios(scenarios_root)
    rows: List[DatasetRow] = []

    for scenario in scenarios:
        prompt = scenario.get("prompt", "")
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
                    context=scenario.get("context", {}),
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
