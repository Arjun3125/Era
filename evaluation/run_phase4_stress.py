#!/usr/bin/env python
"""
Unified Milestone 4 stress runner.

This is a thin orchestrator that executes all stress layers through
`evaluation/run_phase2_robustness.py` to preserve a single evaluation harness.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _build_phase2_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        str(ROOT / ".venv" / "Scripts" / "python.exe"),
        "evaluation/run_phase2_robustness.py",
        "--split-manifest",
        args.split_manifest,
        "--split-name",
        args.split_name,
        "--skip-ablations",
        "--diversity-prompts",
        "--semantic-scorer",
        "--enable-uncertainty-control",
        "--uncertainty-model",
        args.uncertainty_model,
        "--uncertainty-threshold-mode",
        args.uncertainty_threshold_mode,
        "--max-runtime-hours",
        str(args.max_runtime_hours),
        "--force-clear-lock",
    ]
    if args.limit is not None:
        cmd.extend(["--limit", str(args.limit)])

    if args.uncertainty_threshold_mode == "static":
        if args.uncertainty_threshold_1 is not None:
            cmd.extend(["--uncertainty-threshold-1", str(args.uncertainty_threshold_1)])
        if args.uncertainty_threshold_2 is not None:
            cmd.extend(["--uncertainty-threshold-2", str(args.uncertainty_threshold_2)])
        if args.uncertainty_threshold_3 is not None:
            cmd.extend(["--uncertainty-threshold-3", str(args.uncertainty_threshold_3)])

    if args.adversarial_self_play_rounds > 0:
        cmd.extend(
            [
                "--adversarial-self-play-rounds",
                str(args.adversarial_self_play_rounds),
                "--adversarial-self-play-dataset",
                args.adversarial_self_play_dataset,
            ]
        )
    if args.shift_modes:
        cmd.extend(["--shift-modes", args.shift_modes, "--shift-dataset", args.shift_dataset])
    if args.governance_red_team:
        cmd.extend(["--governance-red-team", "--governance-dataset", args.governance_dataset])
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Milestone 4 stress suite via Phase2 runner")
    parser.add_argument("--full", action="store_true", help="Enable all stress layers")
    parser.add_argument(
        "--split-manifest",
        default="evaluation/benchmark_dataset/split_manifest_seed42.json",
    )
    parser.add_argument("--split-name", choices=["train", "val", "test"], default="test")
    parser.add_argument("--uncertainty-model", required=True)
    parser.add_argument(
        "--uncertainty-threshold-mode",
        choices=["runtime_percentile", "static"],
        default="runtime_percentile",
    )
    parser.add_argument("--uncertainty-threshold-1", type=float, default=None)
    parser.add_argument("--uncertainty-threshold-2", type=float, default=None)
    parser.add_argument("--uncertainty-threshold-3", type=float, default=None)
    parser.add_argument("--max-runtime-hours", type=float, default=4.0)
    parser.add_argument("--limit", type=int, default=None)

    parser.add_argument("--adversarial-self-play-rounds", type=int, default=0)
    parser.add_argument(
        "--adversarial-self-play-dataset",
        choices=["core", "adversarial", "ood"],
        default="core",
    )
    parser.add_argument("--shift-modes", default="")
    parser.add_argument("--shift-dataset", choices=["core", "adversarial", "ood"], default="core")
    parser.add_argument("--governance-red-team", action="store_true")
    parser.add_argument("--governance-dataset", choices=["core", "adversarial", "ood"], default="core")

    args = parser.parse_args()

    if args.full:
        args.adversarial_self_play_rounds = max(args.adversarial_self_play_rounds, 2)
        if not args.shift_modes:
            args.shift_modes = "time_pressure,value_conflict,sparse_info"
        args.governance_red_team = True

    cmd = _build_phase2_cmd(args)
    print("[PHASE4] Launching:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
