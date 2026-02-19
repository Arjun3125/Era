#!/usr/bin/env python3
"""
Run bidirectional LLM simulation: User LLM <-> Persona LLM.

No human typing is required in normal mode.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


def _load_dotenv_fallback(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        _load_dotenv_fallback()


class DryRunLLM:
    """Cheap deterministic stand-in for quick smoke tests."""

    def __init__(self, name: str):
        self.name = name

    def speak(self, system_context: str, user_input: str) -> str:
        if "Return only the user message" in user_input:
            return "I am still uncertain and want a clear next step."
        return f"[{self.name}] Based on your message, take one concrete action today and review the result."


def main() -> int:
    _load_env()

    # Allow running from any location while keeping imports repo-local.
    sys.path.insert(0, os.path.dirname(__file__))

    from hse.human_profile import SyntheticHuman
    from hse.simulation import BidirectionalSimulation
    from persona.learning.episodic_memory import EpisodicMemory
    from persona.learning.performance_metrics import PerformanceMetrics
    from persona.ollama_runtime import OllamaRuntime

    parser = argparse.ArgumentParser(description="Bidirectional LLM simulation (User LLM <-> Persona LLM)")
    parser.add_argument("--turns", type=int, default=100, help="Number of turns to simulate")
    parser.add_argument(
        "--user-model",
        default=os.getenv("USER_MODEL", "llama3.1:8b-instruct-q4_0"),
        help="User LLM model",
    )
    parser.add_argument(
        "--persona-model",
        default=os.getenv("PROGRAM_MODEL", "qwen3:14b"),
        help="Persona LLM model",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--save-report",
        default="data/memory/simulation_report.json",
        help="Where to save final report",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose turn-by-turn output")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--dry-run", action="store_true", help="Use stub LLMs (fast smoke test)")
    args = parser.parse_args()

    verbose = True
    if args.quiet:
        verbose = False
    elif args.verbose:
        verbose = True

    print(f"\n{'=' * 80}")
    print("BIDIRECTIONAL LLM SIMULATION LAUNCHER")
    print(f"{'=' * 80}")
    print(f"User Model: {args.user_model}")
    print(f"Persona Model: {args.persona_model}")
    print(f"Turns: {args.turns}")
    print(f"Seed: {args.seed}")
    print(f"Dry Run: {args.dry_run}")
    print(f"{'=' * 80}\n")

    print("[1/5] Initializing LLM runtimes...")
    try:
        if args.dry_run:
            user_llm = DryRunLLM(name="USER")
            persona_llm = DryRunLLM(name="PERSONA")
        else:
            user_llm = OllamaRuntime(speak_model=args.user_model, analyze_model=args.user_model)
            persona_llm = OllamaRuntime(speak_model=args.persona_model, analyze_model=args.persona_model)
        print(f"   [OK] User LLM ready: {args.user_model}")
        print(f"   [OK] Persona LLM ready: {args.persona_model}")
    except Exception as exc:
        print(f"   [ERROR] LLM initialization failed: {exc}")
        return 1

    print("\n[2/5] Initializing learning systems...")
    try:
        episodic_memory = EpisodicMemory(storage_path="data/memory/episodes.jsonl")
        performance_metrics = PerformanceMetrics(storage_path="data/memory/metrics.jsonl")
        print("   [OK] Episodic memory ready")
        print("   [OK] Performance metrics ready")
    except Exception as exc:
        print(f"   [ERROR] Learning systems failed: {exc}")
        return 1

    print("\n[3/5] Creating synthetic human...")
    try:
        human = SyntheticHuman(
            name="Test Subject Alpha",
            age=32,
            profession="Software Engineer",
            seed=args.seed,
        )
        print(f"   [OK] Synthetic human created: {human.name}")
    except Exception as exc:
        print(f"   [ERROR] Failed to create human: {exc}")
        return 1

    print("\n[4/5] Initializing bidirectional simulation...")
    try:
        council = None
        if not args.dry_run:
            # Import lazily to avoid council init overhead in dry-run mode.
            from persona.council import DynamicCouncil

            council = DynamicCouncil(llm=persona_llm)
        simulation = BidirectionalSimulation(
            human=human,
            user_llm=user_llm,
            persona_llm=persona_llm,
            council=council,
            episodic_memory=episodic_memory,
            performance_metrics=performance_metrics,
        )
        print("   [OK] Simulation ready")
    except Exception as exc:
        print(f"   [ERROR] Simulation initialization failed: {exc}")
        return 1

    print(f"\n[5/5] Running simulation ({args.turns} turns)...")
    print(f"       Start time: {datetime.now().isoformat()}")

    try:
        report = simulation.run_conversation(num_turns=args.turns, verbose=verbose)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Simulation stopped by user")
        report = simulation._generate_final_report()
    except Exception as exc:
        print(f"\n[ERROR] Simulation failed: {exc}")
        return 1

    print(f"\n[SAVING] Report to {args.save_report}...")
    simulation.save_report(args.save_report)

    total_turns = report["simulation_metrics"]["total_turns"]
    successful_turns = report["simulation_metrics"]["successful_turns"]
    success_rate = successful_turns / max(1, total_turns)

    print(f"\n{'=' * 80}")
    print("SIMULATION RESULTS")
    print(f"{'=' * 80}")
    print(f"Total turns: {total_turns}")
    print(f"Success rate: {success_rate:.0%}")
    print(f"Crises triggered: {report['simulation_metrics']['crises_triggered']}")
    print(f"Mode switches: {report['simulation_metrics']['mode_switches']}")
    print(f"Final emotional load: {report['final_emotional_load']:.0%}")
    print(f"Conversation exchanges: {len(report['conversation_history'])}")
    print(f"{'=' * 80}\n")
    print(f"[OK] Simulation complete. Report: {args.save_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
