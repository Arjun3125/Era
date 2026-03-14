"""Dataset builder for learned minister policies."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from modules.learning_core import augment_context_with_knowledge


@dataclass
class PolicyRow:
    scenario_id: str
    minister: str
    prompt: str
    context: Dict[str, Any]
    stance: str
    confidence: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "minister": self.minister,
            "prompt": self.prompt,
            "context": self.context,
            "stance": self.stance,
            "confidence": self.confidence,
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
) -> List[PolicyRow]:
    from modules.council_execution.engine import NativeCouncil

    council = NativeCouncil()
    scenarios = load_scenarios(scenarios_root)
    rows: List[PolicyRow] = []

    for scenario in scenarios:
        prompt = scenario.get("prompt", "")
        context = augment_context_with_knowledge(scenario.get("context", {}), prompt)
        for name, minister in council.ministers.items():
            result = minister.analyze(prompt, context)
            stance = str(result.get("stance", "neutral")).strip().lower()
            confidence = float(result.get("confidence", 0.0) or 0.0)
            rows.append(
                PolicyRow(
                    scenario_id=str(scenario.get("scenario_id", "")),
                    minister=str(name),
                    prompt=prompt,
                    context=context,
                    stance=stance,
                    confidence=max(0.0, min(1.0, confidence)),
                )
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.as_dict(), ensure_ascii=True))
            handle.write("\n")
    return rows


def load_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def filter_by_minister(rows: Iterable[Dict[str, Any]], minister: str) -> List[Dict[str, Any]]:
    target = str(minister).strip().lower()
    return [row for row in rows if str(row.get("minister", "")).strip().lower() == target]
