#!/usr/bin/env python
"""
Step-0 KIS failure-mode diagnosis.

Pull hardest high-U failures from Phase2 results and summarize:
- required vs matched principles
- triggered failure modes
- inferred underweighted domains (from missing principles)
- retrieval/evaluator bottleneck indicators
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.scoring.outcome_scorer import PRINCIPLE_KEYWORDS


DEFAULT_RESULTS = "evaluation/results/phase2_robustness_results_test_control_darbar_strengthened.json"
DEFAULT_BENCH = "evaluation/benchmark_dataset"
DEFAULT_OUT_JSON = "evaluation/results/kis_failure_mode_diagnosis.json"
DEFAULT_OUT_MD = "evaluation/results/KIS_FAILURE_MODE_DIAGNOSIS.md"


PRINCIPLE_DOMAIN_MAP: Dict[str, str] = {
    "optionality": "optionality",
    "optionality_timing": "optionality",
    "downside_asymmetry": "risk",
    "reversibility": "optionality",
    "feedback_loops": "information",
    "systemic_barriers": "systems",
    "time_value": "temporal",
    "information_value": "information",
    "long_term_impact": "long_horizon",
    "relationship_stability_verification": "relationship",
    "network_rebuilding_capacity": "career_network",
}


def _domain_for_principle(principle: str) -> str:
    key = str(principle or "").strip().lower()
    return PRINCIPLE_DOMAIN_MAP.get(key, f"unmapped:{key}" if key else "unmapped:unknown")


def _load_benchmark_index(benchmark_dir: Path) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for file in sorted(benchmark_dir.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for row in data:
                sid = str(row.get("id", "")).strip()
                if sid:
                    index[sid] = row
    return index


def _iter_council_rows(results: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    raw_runs = (results.get("raw_runs") or {})
    for run_name, payload in raw_runs.items():
        if not str(run_name).endswith("_council"):
            continue
        conf = (payload or {}).get("confidence_records") or []
        out = ((payload or {}).get("outcome_summary") or {}).get("results") or []
        n = min(len(conf), len(out))
        for i in range(n):
            yield run_name, conf[i], out[i]


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _top_items(counter: Counter, k: int = 10) -> List[Tuple[str, int]]:
    return [(str(name), int(count)) for name, count in counter.most_common(k)]


def analyze(
    results_path: Path,
    benchmark_dir: Path,
    *,
    limit: int,
    score_threshold: float,
    high_u_threshold: float | None,
    dominance_threshold: float,
) -> Dict[str, Any]:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    benchmark = _load_benchmark_index(benchmark_dir)

    t1_meta = (
        ((results.get("metadata") or {}).get("uncertainty_threshold_1"))
    )
    high_u = float(high_u_threshold if high_u_threshold is not None else (t1_meta if t1_meta is not None else 0.0))

    all_low_score: List[Dict[str, Any]] = []
    all_high_u_low_score: List[Dict[str, Any]] = []

    missing_principles_counter: Counter = Counter()
    underweighted_domains_counter: Counter = Counter()
    failure_modes_counter: Counter = Counter()
    unsupported_principles_counter: Counter = Counter()

    dominant_vote_count = 0
    memory_recall_count = 0
    kis_signal_count = 0
    total_rows = 0

    for run_name, rec, out in _iter_council_rows(results):
        rec_score = rec.get("score")
        out_score = (out or {}).get("score")
        score = _to_float(out_score if rec_score is None else rec_score)
        u = _to_float(rec.get("uncertainty_composite"), default=-1.0)
        sid = str(rec.get("scenario_id", "")).strip()
        scenario = benchmark.get(sid, {})
        rubric = scenario.get("ground_truth_rubric", {}) if isinstance(scenario, dict) else {}
        required = list(rubric.get("principles_required", []) or [])
        matched = list((out or {}).get("principles_satisfied", []) or [])
        matched_set = {str(x) for x in matched}
        missing = [str(p) for p in required if str(p) not in matched_set]
        failure_modes = list((out or {}).get("failure_modes_matched", []) or [])
        unsupported = [p for p in required if str(p) not in PRINCIPLE_KEYWORDS]
        domains = sorted({_domain_for_principle(p) for p in missing})

        uncertainty = (rec.get("uncertainty") or {})
        vote_conc = _to_float(uncertainty.get("vote_concentration_index"), default=0.0)
        dominant_vote = vote_conc >= dominance_threshold
        control_policy = (rec.get("control_policy") or {})
        memory_recall = bool(control_policy.get("enable_memory_recall"))
        kis_present = uncertainty.get("kis_variance") is not None

        row = {
            "run_name": run_name,
            "scenario_id": sid,
            "seed": rec.get("seed"),
            "distribution": rec.get("distribution"),
            "score": score,
            "uncertainty_u": u,
            "decision_path": rec.get("decision_path"),
            "path_matched": bool((out or {}).get("path_matched", False)),
            "required_principles": required,
            "matched_principles": matched,
            "missing_principles": missing,
            "underweighted_domains": domains,
            "failure_modes_triggered": failure_modes,
            "unsupported_required_principles": unsupported,
            "dominant_vote": dominant_vote,
            "vote_concentration_index": vote_conc,
            "memory_recall_enabled": memory_recall,
            "kis_signal_present": kis_present,
            "control_mode": (control_policy or {}).get("target_mode"),
        }

        if score < score_threshold:
            all_low_score.append(row)
            if u >= high_u:
                all_high_u_low_score.append(row)

        total_rows += 1
        if dominant_vote:
            dominant_vote_count += 1
        if memory_recall:
            memory_recall_count += 1
        if kis_present:
            kis_signal_count += 1

        for p in missing:
            missing_principles_counter[p] += 1
            underweighted_domains_counter[_domain_for_principle(p)] += 1
        for fm in failure_modes:
            failure_modes_counter[str(fm)] += 1
        for p in unsupported:
            unsupported_principles_counter[str(p)] += 1

    all_high_u_low_score.sort(key=lambda r: (r["score"], -r["uncertainty_u"]))
    hardest = all_high_u_low_score[:limit]

    hard_missing_counter: Counter = Counter()
    hard_domain_counter: Counter = Counter()
    hard_failure_counter: Counter = Counter()
    hard_unsupported_counter: Counter = Counter()

    info_gap_count = 0
    path_mismatch_count = 0
    both_count = 0
    for row in hardest:
        miss = row["missing_principles"]
        path_ok = row["path_matched"]
        if miss:
            info_gap_count += 1
        if not path_ok:
            path_mismatch_count += 1
        if miss and (not path_ok):
            both_count += 1
        for p in miss:
            hard_missing_counter[p] += 1
            hard_domain_counter[_domain_for_principle(p)] += 1
        for fm in row["failure_modes_triggered"]:
            hard_failure_counter[fm] += 1
        for p in row["unsupported_required_principles"]:
            hard_unsupported_counter[p] += 1

    n_hard = len(hardest)
    summary = {
        "results_file": str(results_path),
        "score_threshold": score_threshold,
        "high_u_threshold": high_u,
        "rows_total_council": total_rows,
        "rows_score_below_threshold": len(all_low_score),
        "rows_high_u_and_score_below_threshold": len(all_high_u_low_score),
        "hardest_selected": n_hard,
        "diagnostic_signals": {
            "dominant_vote_rate_all_rows": (dominant_vote_count / total_rows) if total_rows else 0.0,
            "memory_recall_enabled_rate_all_rows": (memory_recall_count / total_rows) if total_rows else 0.0,
            "kis_signal_present_rate_all_rows": (kis_signal_count / total_rows) if total_rows else 0.0,
        },
        "hardest_patterns": {
            "info_gap_rate": (info_gap_count / n_hard) if n_hard else 0.0,
            "path_mismatch_rate": (path_mismatch_count / n_hard) if n_hard else 0.0,
            "both_info_gap_and_path_mismatch_rate": (both_count / n_hard) if n_hard else 0.0,
            "top_missing_principles": _top_items(hard_missing_counter, 12),
            "top_underweighted_domains": _top_items(hard_domain_counter, 12),
            "top_failure_modes_triggered": _top_items(hard_failure_counter, 12),
            "top_unsupported_required_principles": _top_items(hard_unsupported_counter, 12),
        },
        "global_patterns": {
            "top_missing_principles": _top_items(missing_principles_counter, 12),
            "top_underweighted_domains": _top_items(underweighted_domains_counter, 12),
            "top_failure_modes_triggered": _top_items(failure_modes_counter, 12),
            "top_unsupported_required_principles": _top_items(unsupported_principles_counter, 12),
        },
    }

    # Bottleneck inference (explicitly heuristic).
    hard = summary["hardest_patterns"]
    unsupported_hard = sum(c for _, c in hard["top_unsupported_required_principles"])
    failure_modes_hard = sum(c for _, c in hard["top_failure_modes_triggered"])
    kis_present_rate = summary["diagnostic_signals"]["kis_signal_present_rate_all_rows"]
    rationale_keyword_gap_like = (
        hard["info_gap_rate"] >= 0.8
        and hard["path_mismatch_rate"] <= 0.2
        and failure_modes_hard == 0
    )
    retrieval_like = (
        hard["info_gap_rate"] >= 0.6
        and len(hard["top_underweighted_domains"]) > 0
        and kis_present_rate > 0.0
    )
    if rationale_keyword_gap_like and unsupported_hard > 0:
        bottleneck = "evaluator_misalignment_likely (rubric/scorer vocabulary gaps)"
    elif rationale_keyword_gap_like:
        bottleneck = "evaluator_or_prompt_keyword_coverage_likely"
    elif retrieval_like:
        bottleneck = "retrieval_or_knowledge_coverage_likely"
    elif kis_present_rate == 0.0:
        bottleneck = "inconclusive_no_kis_telemetry"
    else:
        bottleneck = "inconclusive_from_current_logs"
    summary["inference"] = {
        "bottleneck_hypothesis": bottleneck,
        "note": (
            "Heuristic inference from logged outputs. "
            "Domain underweighting is inferred from missing required principles."
        ),
    }

    return {
        "summary": summary,
        "hardest_cases": hardest,
    }


def write_markdown(report: Dict[str, Any], out_path: Path) -> None:
    s = report["summary"]
    lines: List[str] = []
    lines.append("# KIS Step-0 Failure Diagnosis")
    lines.append("")
    lines.append(f"- Results file: `{s['results_file']}`")
    lines.append(f"- Score threshold: `{s['score_threshold']}`")
    lines.append(f"- High-U threshold: `{s['high_u_threshold']:.6f}`")
    lines.append(f"- Council rows analyzed: `{s['rows_total_council']}`")
    lines.append(f"- Rows with score<threshold: `{s['rows_score_below_threshold']}`")
    lines.append(f"- Rows with high-U and score<threshold: `{s['rows_high_u_and_score_below_threshold']}`")
    lines.append(f"- Hardest selected: `{s['hardest_selected']}`")
    lines.append("")
    lines.append("## Bottleneck Inference")
    lines.append(f"- Hypothesis: `{s['inference']['bottleneck_hypothesis']}`")
    lines.append(f"- Note: {s['inference']['note']}")
    lines.append("")
    lines.append("## Hardest Pattern Snapshot")
    hard = s["hardest_patterns"]
    lines.append(f"- Info-gap rate: `{hard['info_gap_rate']:.3f}`")
    lines.append(f"- Path-mismatch rate: `{hard['path_mismatch_rate']:.3f}`")
    lines.append(f"- Both rate: `{hard['both_info_gap_and_path_mismatch_rate']:.3f}`")
    lines.append("- Top missing principles:")
    for k, v in hard["top_missing_principles"]:
        lines.append(f"  - {k}: {v}")
    lines.append("- Top underweighted domains:")
    for k, v in hard["top_underweighted_domains"]:
        lines.append(f"  - {k}: {v}")
    lines.append("- Top triggered failure modes:")
    for k, v in hard["top_failure_modes_triggered"]:
        lines.append(f"  - {k}: {v}")
    lines.append("- Unsupported required principles (scorer vocabulary gap):")
    for k, v in hard["top_unsupported_required_principles"]:
        lines.append(f"  - {k}: {v}")
    lines.append("")
    lines.append("## Hardest Cases")
    for idx, row in enumerate(report["hardest_cases"], start=1):
        lines.append(
            f"{idx}. `{row['scenario_id']}` seed={row['seed']} dist={row['distribution']} "
            f"score={row['score']:.3f} U={row['uncertainty_u']:.3f} "
            f"path_matched={row['path_matched']} mode={row.get('control_mode')}"
        )
        lines.append(f"   required: {row['required_principles']}")
        lines.append(f"   matched: {row['matched_principles']}")
        lines.append(f"   missing: {row['missing_principles']}")
        lines.append(f"   underweighted_domains: {row['underweighted_domains']}")
        lines.append(f"   failure_modes_triggered: {row['failure_modes_triggered']}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose KIS failure mode from Phase2 logs.")
    parser.add_argument("--results-json", default=DEFAULT_RESULTS)
    parser.add_argument("--benchmark-dir", default=DEFAULT_BENCH)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--score-threshold", type=float, default=0.6)
    parser.add_argument("--high-u-threshold", type=float, default=None)
    parser.add_argument("--dominance-threshold", type=float, default=0.75)
    parser.add_argument("--output-json", default=DEFAULT_OUT_JSON)
    parser.add_argument("--output-md", default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    report = analyze(
        Path(args.results_json),
        Path(args.benchmark_dir),
        limit=max(1, int(args.limit)),
        score_threshold=float(args.score_threshold),
        high_u_threshold=args.high_u_threshold,
        dominance_threshold=float(args.dominance_threshold),
    )

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, Path(args.output_md))

    print(f"Saved JSON: {out_json}")
    print(f"Saved MD: {args.output_md}")
    print(f"Bottleneck hypothesis: {report['summary']['inference']['bottleneck_hypothesis']}")
    print(
        "Hardest high-U failures selected: "
        f"{report['summary']['hardest_selected']} "
        f"(pool={report['summary']['rows_high_u_and_score_below_threshold']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
