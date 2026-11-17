#!/usr/bin/env python3
"""Analyze textbook scoring dataset and emit a markdown summary report.

Usage:
  python research/tools/analyze_dataset.py \
    --input research/data/processed/dataset_master.csv \
    --output research/reports/summary.md
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

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

REQUIRED_COLUMNS = {"subject", *DIMENSIONS}


def to_float(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Input CSV has no header row.")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")
        return list(reader)


def summarize(rows: list[dict[str, str]]) -> tuple[dict[str, float], dict[str, dict[str, float]], int]:
    dim_values: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    subject_dim_values: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {d: [] for d in DIMENSIONS}
    )
    valid_rows = 0

    for row in rows:
        subject = (row.get("subject") or "").strip() or "Unknown"
        row_has_score = False
        for dim in DIMENSIONS:
            value = to_float(row.get(dim, ""))
            if value is None:
                continue
            row_has_score = True
            dim_values[dim].append(value)
            subject_dim_values[subject][dim].append(value)
        if row_has_score:
            valid_rows += 1

    overall = {
        dim: round(mean(values), 3)
        for dim, values in dim_values.items()
        if values
    }
    by_subject: dict[str, dict[str, float]] = {}
    for subject, dim_map in subject_dim_values.items():
        by_subject[subject] = {
            dim: round(mean(values), 3)
            for dim, values in dim_map.items()
            if values
        }
    return overall, by_subject, valid_rows


def render_markdown(overall: dict[str, float], by_subject: dict[str, dict[str, float]], valid_rows: int) -> str:
    lines = []
    lines.append("# Dataset Summary Report")
    lines.append("")
    lines.append(f"Scored rows detected: **{valid_rows}**")
    lines.append("")
    lines.append("## Overall Dimension Averages")
    lines.append("")
    lines.append("| Dimension | Mean Score |")
    lines.append("|---|---:|")
    for dim in DIMENSIONS:
        score = overall.get(dim)
        lines.append(f"| {dim} | {'' if score is None else score} |")

    lines.append("")
    lines.append("## Subject-wise Dimension Averages")
    lines.append("")

    for subject in sorted(by_subject):
        lines.append(f"### {subject}")
        lines.append("")
        lines.append("| Dimension | Mean Score |")
        lines.append("|---|---:|")
        dim_map = by_subject[subject]
        for dim in DIMENSIONS:
            score = dim_map.get(dim)
            lines.append(f"| {dim} | {'' if score is None else score} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = load_rows(args.input)
    overall, by_subject, valid_rows = summarize(rows)
    report = render_markdown(overall, by_subject, valid_rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")

    print(f"Report written: {args.output}")


if __name__ == "__main__":
    main()
