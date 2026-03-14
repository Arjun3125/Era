"""Run failure analysis on benchmark traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.evaluation_engine.calibration import calibration_bins
from modules.failure_analysis import (
    analyze_traces,
    plot_calibration_curve,
    plot_category_accuracy,
    plot_failure_distribution,
)
from modules.failure_analysis.report_generator import write_report


def _load_traces(path: Path) -> list[dict]:
    traces = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            traces.append(json.loads(line))
    return traces


def main() -> None:
    parser = argparse.ArgumentParser(description="Run failure analysis on traces.jsonl.")
    parser.add_argument("--traces", required=True, help="Path to traces.jsonl.")
    parser.add_argument("--output", default="reports/failure_report.md")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--clusters", type=int, default=0, help="Number of failure clusters to compute.")
    parser.add_argument("--cluster-min-size", type=int, default=2, help="Minimum failures per cluster.")
    parser.add_argument("--cluster-top-terms", type=int, default=5, help="Top terms per cluster.")
    parser.add_argument("--plots-dir", default=None, help="Optional directory to write failure plots.")
    args = parser.parse_args()

    traces = _load_traces(Path(args.traces))
    analysis = analyze_traces(
        traces,
        top_k=args.top_k,
        cluster_count=args.clusters,
        cluster_min_size=args.cluster_min_size,
        cluster_top_terms=args.cluster_top_terms,
    )
    write_report(Path(args.output), analysis)
    print(f"Wrote failure analysis report to {args.output}")

    if args.plots_dir:
        plots_dir = Path(args.plots_dir)
        plot_failure_distribution(analysis.failure_type_counts, plots_dir)
        plot_category_accuracy(analysis.category_accuracy, plots_dir)

        bins = calibration_bins(
            [
                {
                    "confidence": trace.get("confidence_calibrated", trace.get("confidence", 0.0)),
                    "correct": bool(trace.get("decision_correct", 0)),
                }
                for trace in traces
            ]
        )
        plot_calibration_curve(
            [b.confidence_avg for b in bins],
            [b.accuracy for b in bins],
            plots_dir,
        )


if __name__ == "__main__":
    main()
