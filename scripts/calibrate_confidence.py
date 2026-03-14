"""Fit temperature scaling on benchmark results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Tuple

from modules.uncertainty.calibration import fit_temperature


def _load_results(path: Path) -> Tuple[list[float], list[int]]:
    confidences: list[float] = []
    labels: list[int] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if "era" in payload:
                era = payload["era"]
                confidence = era.get("confidence", 0.0)
                correct = era.get("decision_correct", 0)
            else:
                confidence = payload.get("confidence", 0.0)
                correct = payload.get("decision_correct", 0)
            confidences.append(float(confidence))
            labels.append(int(correct))
    return confidences, labels


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit temperature scaling for confidence calibration.")
    parser.add_argument("--results", required=True, help="Path to results.jsonl with confidences.")
    parser.add_argument("--output", default="data/calibration/temperature.json")
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found: {results_path}")

    confidences, labels = _load_results(results_path)
    calibrator = fit_temperature(confidences, labels)
    output_path = Path(args.output)
    calibrator.save(output_path)
    print(json.dumps({"temperature": calibrator.temperature}, indent=2))


if __name__ == "__main__":
    main()
