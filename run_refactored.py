#!/usr/bin/env python3
"""Refactored orchestration entrypoint without legacy persona/sovereign runtime."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from modules.decision_pipeline import DecisionPipelineEngine


def _run_once(
    *,
    pipeline: DecisionPipelineEngine,
    user_input: str,
    requested_mode: str | None,
) -> Dict[str, Any]:
    result = pipeline.run(
        user_input=user_input,
        requested_mode=requested_mode,
        source="run_refactored",
    )
    return {
        "status": result.status,
        "run_id": result.run_id,
        "mode": result.mode_resolution.mode,
        "should_invoke_council": bool(result.mode_resolution.should_invoke_council),
        "selected_ministers": list(result.mode_resolution.selected_ministers or []),
        "decision": result.decision_contract.decision,
        "confidence": float(result.decision_contract.confidence),
        "rationale": result.decision_contract.rationale,
        "final_decision": dict(result.final_decision or {}),
        "error_count": len(result.errors),
        "errors": list(result.errors),
        "warnings": [
            issue.message
            for issue in list(result.pipeline_issues or [])
            if str(issue.severity).lower() in {"warning", "warn"}
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the refactored decision pipeline (legacy-free runtime path)."
    )
    parser.add_argument(
        "--input",
        dest="user_input",
        default=None,
        help="Single-run input. If omitted, launches interactive loop.",
    )
    parser.add_argument(
        "--mode",
        dest="requested_mode",
        default=None,
        help="Requested mode (quick/meeting/war/darbar/baseline).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict orchestrator behavior.",
    )
    args = parser.parse_args()

    pipeline = DecisionPipelineEngine.create(strict=bool(args.strict))

    if args.user_input:
        payload = _run_once(
            pipeline=pipeline,
            user_input=args.user_input,
            requested_mode=args.requested_mode,
        )
        print(json.dumps(payload, indent=2))
        return 0

    print("Refactored pipeline interactive mode. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("input> ").strip()
        except EOFError:
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break
        payload = _run_once(
            pipeline=pipeline,
            user_input=user_input,
            requested_mode=args.requested_mode,
        )
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
