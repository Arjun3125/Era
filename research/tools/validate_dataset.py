#!/usr/bin/env python3
"""Validate textbook scoring dataset quality.

Checks:
1. Required columns exist.
2. Score columns contain numeric values in range [1, 5] when present.
3. `mean_score` matches computed mean (tolerance configurable) when provided.

Usage:
  python research/tools/validate_dataset.py \
    --input research/data/processed/dataset_master.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

DIMENSIONS = [
    "curriculum_alignment",
    "sequencing_scaffolding",
    "language_readability",
    "worked_examples",
    "exercise_diversity",
    "competency_hots",
    "inclusivity_context",
    "visual_design",
]

REQUIRED_COLUMNS = {"subject", *DIMENSIONS, "mean_score"}


def to_float(raw: str) -> float | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def validate_file(path: Path, tolerance: float = 0.01) -> tuple[bool, list[str]]:
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return False, ["CSV has no header row."]

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            return False, [f"Missing required columns: {sorted(missing)}"]

        for line_no, row in enumerate(reader, start=2):
            scores: list[float] = []
            for dim in DIMENSIONS:
                value = to_float(row.get(dim, ""))
                if value is None:
                    continue
                if not (1 <= value <= 5):
                    errors.append(
                        f"Line {line_no}: {dim}={value} is out of range [1,5]."
                    )
                scores.append(value)

            mean_raw = to_float(row.get("mean_score", ""))
            if mean_raw is not None and scores:
                computed = sum(scores) / len(scores)
                if abs(computed - mean_raw) > tolerance:
                    errors.append(
                        f"Line {line_no}: mean_score={mean_raw} differs from computed={computed:.3f}."
                    )

    return len(errors) == 0, errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=0.01)
    args = parser.parse_args()

    ok, errors = validate_file(args.input, tolerance=args.tolerance)
    if ok:
        print("Dataset validation passed.")
        raise SystemExit(0)

    print("Dataset validation failed:")
    for err in errors:
        print(f"- {err}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
