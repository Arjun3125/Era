#!/usr/bin/env python3
"""Refactored orchestration entrypoint without legacy persona/sovereign runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from decision_env import (
    SCENARIO_DOMAINS,
    DecisionEnvironment,
    EpisodeRunner,
    EraDecisionAgent,
    LongHorizonDecisionEnvironment,
    LongHorizonEpisodeRunner,
    MultiStepDecisionEnvironment,
    MultiStepEpisodeRunner,
    ScenarioGenerator,
)
from modules.decision_pipeline import DecisionPipelineEngine


def _run_once(
    *,
    pipeline: DecisionPipelineEngine,
    user_input: str,
    requested_mode: str | None,
    routing_context: Dict[str, Any] | None,
) -> Dict[str, Any]:
    result = pipeline.run(
        user_input=user_input,
        requested_mode=requested_mode,
        routing_context=routing_context,
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


def _run_simulation(
    *,
    requested_mode: str | None,
    strict: bool,
    episode_count: int,
    scenario_domain: str | None,
    seed: int | None,
    experience_log: str | None,
    simulate_steps: int,
    long_horizon: bool,
) -> Dict[str, Any]:
    pipeline = DecisionPipelineEngine.create(strict=strict)
    agent = EraDecisionAgent(pipeline=pipeline, requested_mode=requested_mode or "meeting")
    if long_horizon:
        environment = LongHorizonDecisionEnvironment(
            generator=ScenarioGenerator(seed=seed),
            default_domain=scenario_domain,
            max_steps=simulate_steps or 24,
        )
        runner = LongHorizonEpisodeRunner(environment=environment, agent=agent)
        episodes = runner.run_training_loop(episode_count=episode_count)
        if experience_log:
            log_path = Path(experience_log)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("w", encoding="utf-8") as handle:
                for episode in episodes:
                    handle.write(json.dumps(episode.as_dict(), ensure_ascii=True))
                    handle.write("\n")
        payload = {
            "episode_count": episode_count,
            "episodes": [episode.as_dict() for episode in episodes],
        }
        payload["requested_mode"] = requested_mode or "meeting"
        payload["scenario_domain"] = scenario_domain or "mixed"
        payload["seed"] = seed
        payload["simulate_steps"] = simulate_steps
        payload["experience_log"] = experience_log
        return payload
    if simulate_steps and simulate_steps > 1:
        environment = MultiStepDecisionEnvironment(
            generator=ScenarioGenerator(seed=seed),
            default_domain=scenario_domain,
            max_steps=simulate_steps,
        )
        runner = MultiStepEpisodeRunner(environment=environment, agent=agent)
        summary = runner.run_training_loop(
            episode_count=episode_count,
            domain=scenario_domain,
            experience_log_path=experience_log,
        )
    else:
        environment = DecisionEnvironment(
            generator=ScenarioGenerator(seed=seed),
            default_domain=scenario_domain,
        )
        runner = EpisodeRunner(environment=environment, agent=agent)
        summary = runner.run_training_loop(
            episode_count=episode_count,
            domain=scenario_domain,
            experience_log_path=experience_log,
        )
    payload = summary.as_dict()
    payload["requested_mode"] = requested_mode or "meeting"
    payload["scenario_domain"] = scenario_domain or "mixed"
    payload["seed"] = seed
    payload["simulate_steps"] = simulate_steps
    payload["experience_log"] = experience_log
    return payload


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
    parser.add_argument(
        "--simulate-episodes",
        type=int,
        default=0,
        help="Run the embedded decision environment for N episodes.",
    )
    parser.add_argument(
        "--simulate-steps",
        type=int,
        default=1,
        help="Number of steps per episode when simulating (1 = one-step).",
    )
    parser.add_argument(
        "--long-horizon",
        action="store_true",
        help="Use the long-horizon strategic simulation environment.",
    )
    parser.add_argument(
        "--scenario-domain",
        default=None,
        help=(
            "Restrict simulated scenarios to one domain: "
            + "/".join(SCENARIO_DOMAINS)
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional RNG seed for scenario generation.",
    )
    parser.add_argument(
        "--experience-log",
        default=None,
        help="Optional JSONL output path for episode records in simulation mode.",
    )
    parser.add_argument(
        "--routing-context",
        default=None,
        help="Optional JSON dict for routing context overrides (expert router, etc).",
    )
    args = parser.parse_args()

    if args.simulate_episodes < 0:
        parser.error("--simulate-episodes must be zero or positive.")
    if args.simulate_episodes > 0 and args.user_input:
        parser.error("--input cannot be combined with --simulate-episodes.")
    if args.scenario_domain:
        normalized_domain = str(args.scenario_domain).strip().lower()
        if normalized_domain not in SCENARIO_DOMAINS:
            parser.error(
                "--scenario-domain must be one of: "
                + ", ".join(SCENARIO_DOMAINS)
            )
        args.scenario_domain = normalized_domain

    if args.simulate_episodes > 0:
        payload = _run_simulation(
            requested_mode=args.requested_mode,
            strict=bool(args.strict),
            episode_count=args.simulate_episodes,
            scenario_domain=args.scenario_domain,
            seed=args.seed,
            experience_log=args.experience_log,
            simulate_steps=args.simulate_steps,
            long_horizon=bool(args.long_horizon),
        )
        print(json.dumps(payload, indent=2))
        return 0

    pipeline = DecisionPipelineEngine.create(strict=bool(args.strict))
    routing_context = None
    if args.routing_context:
        try:
            routing_context = json.loads(args.routing_context)
        except json.JSONDecodeError as exc:
            parser.error(f"--routing-context must be valid JSON: {exc}")

    if args.user_input:
        payload = _run_once(
            pipeline=pipeline,
            user_input=args.user_input,
            requested_mode=args.requested_mode,
            routing_context=routing_context,
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
            routing_context=routing_context,
        )
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
