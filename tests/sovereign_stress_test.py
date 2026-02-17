"""
Sovereign ML Stress Test

Runs a multi-agent stress loop and invokes the ML orchestrator each turn.

Features:
- Dry-run mode (no Ollama calls) for local validation
- Auto-select models if not provided
- Passes conversation (USER + PROGRAM) into ML via `process_decision`
- Periodic retraining via `--retrain-interval`

Usage:
    python sovereign_stress_test.py --dry-run
    python sovereign_stress_test.py --max-turns 50

Note: This script expects the ML orchestrator at `ml/ml_orchestrator.py`.
"""

import subprocess
import time
import random
import signal
import sys
import argparse
from datetime import datetime
import asyncio

# Memory + DARBAR + reward imports
from ml.vector_memory import VectorMemory
from ml.darbar import darbar_debate
from ml.reward_shaping import reward_function

# Import ML orchestrator (adapt to repo's class)
from ml.ml_orchestrator import MLWisdomOrchestrator as MLOrchestrator

# Optional: auto-detect models
from llm.ollama_model_selector import select_models

# -------------------------
# CLI args
# -------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", help="Do not call Ollama; use canned LLM outputs")
parser.add_argument("--max-turns", type=int, default=100, help="Maximum turns to run")
parser.add_argument("--retrain-interval", type=int, default=20, help="Run retrain every N turns (0 to disable)")
parser.add_argument("--user-model", type=str, default=None, help="User LLM model name")
parser.add_argument("--program-model", type=str, default=None, help="Program LLM model name")
parser.add_argument("--workers", type=int, default=1, help="Number of parallel simulation workers (async)")
args = parser.parse_args()

# -------------------------
# Configuration
# -------------------------
USER_MODEL = args.user_model
PROGRAM_MODEL = args.program_model
MAX_TURNS = args.max_turns
RETRAIN_INTERVAL = args.retrain_interval
DRY_RUN = args.dry_run

MODES = ["QUICK", "WAR", "MEETING", "DARBAR"]
RUNNING = True
conversation = []

# Initialize Vector Memory
memory = VectorMemory()

# -------------------------
# Signal handler
# -------------------------
def signal_handler(sig, frame):
    global RUNNING
    print("\n\n=== STOPPING SIMULATION ===")
    RUNNING = False

signal.signal(signal.SIGINT, signal_handler)

# -------------------------
# Model call wrapper
# -------------------------

def call_model(model, prompt, timeout=30):
    """Call Ollama; in DRY_RUN returns a canned response."""
    if DRY_RUN:
        # Simple canned response that varies with prompt and model
        prefix = "[DRY_USER]" if model == USER_MODEL else "[DRY_PROGRAM]"
        sample = f"{prefix} simulated response at {datetime.utcnow().isoformat()}"
        return sample

    # Real invocation
    proc = subprocess.Popen(["ollama", "run", model], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate(timeout=5)
        out = (out or "") + f"\n[TIMEOUT after {timeout}s]"
    return (out or "").strip()

# -------------------------
# Auto-select models if not provided
# -------------------------
if USER_MODEL is None or PROGRAM_MODEL is None:
    u, p = select_models(preferred=["deepseek", "qwen3", "qwen"])  # preference order
    if USER_MODEL is None:
        USER_MODEL = u or "deepseek-r1:8b"
    if PROGRAM_MODEL is None:
        PROGRAM_MODEL = p or USER_MODEL

# Initialize ML system
ml_system = MLOrchestrator()

print("\n=== SOVEREIGN ML STRESS TEST STARTED ===\n")
print(f"USER_MODEL={USER_MODEL} PROGRAM_MODEL={PROGRAM_MODEL} DRY_RUN={DRY_RUN} WORKERS={args.workers}")


def _log_turn(turn_id: int, mode: str, user_msg: str, program_msg: str, ml_result: dict):
    try:
        with open("sovereign_ml_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{datetime.now()} | TURN {turn_id} | MODE {mode}\n")
            f.write(f"USER: {user_msg}\n")
            f.write(f"PROGRAM: {program_msg}\n")
            f.write(f"ML_RESULT: {ml_result}\n")
    except Exception as e:
        print(f"[WARN] Failed to write log: {e}")


def _detect_failure(ml_result: dict) -> bool:
    # Heuristic: error OR missing KIS output considered a failure worth storing
    if not ml_result:
        return True
    if ml_result.get("error"):
        return True
    q = ml_result.get("quality", {})
    if not q.get("has_kis_output", False):
        return True
    return False


def run_sync_instance(instance_id: int = 0, max_turns: int = MAX_TURNS):
    turn = 0
    while RUNNING and (turn < max_turns):
        turn += 1
        mode = random.choice(MODES)

        print(f"\n========== TURN {turn} | MODE: {mode} (instance {instance_id}) ==========")

        # USER LLM (Aggressive Tester)
        user_prompt = f"""
You are a hostile power user.
Test all system features.
Force edge cases.
Switch modes.
Conversation:
{conversation[-10:]}
Continue.
"""

        user_msg = call_model(USER_MODEL, user_prompt)
        conversation.append(("USER", user_msg))

        print("[USER LLM]\n")
        print(user_msg)

        # Prepare program prompt and inject similar past failures from memory
        program_prompt = f"""
You are Sovereign system.
Mode: {mode}
Respond strictly according to mode logic.

Conversation:
{conversation[-10:]}
"""

        similar_cases = memory.search(user_msg)
        if similar_cases:
            program_prompt += "\nRelevant Past Failures:\n"
            for case in similar_cases:
                program_prompt += case + "\n"

        # DARBAR special handling
        if mode == "DARBAR":
            ministers, final = darbar_debate(program_prompt, call_model, PROGRAM_MODEL, dry_run=DRY_RUN)
            program_msg = final
            # append minister opinions to conversation for traceability
            for i, m in enumerate(ministers):
                conversation.append((f"MINISTER_{i+1}", m))
        else:
            program_msg = call_model(PROGRAM_MODEL, program_prompt)
            conversation.append(("PROGRAM", program_msg))

        print("\n[PROGRAM LLM]\n")
        print(program_msg)

        # === REAL ML INTEGRATION ===
        combined_input = f"MODE: {mode}\nUSER: {user_msg}\nPROGRAM: {program_msg}\n"

        try:
            ml_result = ml_system.process_decision(user_input=combined_input)
        except Exception as e:
            ml_result = {"error": str(e)}

        print("\n[ML SYSTEM]\n")
        print(ml_result)

        # Logging
        _log_turn(turn, mode, user_msg, program_msg, ml_result)

        # Memory reinforcement: store failures and strong responses
        failure = _detect_failure(ml_result)
        if failure:
            memory.add(f"{mode} | USER: {user_msg} | PROGRAM: {program_msg}")

        # Example reward shaping usage (record or debug)
        try:
            features = ml_result.get("for_training", {}).get("situation_features", {})
            reward = reward_function(mode, features)
            # append reward to log for inspection
            print(f"[REWARD] mode={mode} reward={reward}")
        except Exception:
            pass

        # Periodic retrain
        if RETRAIN_INTERVAL and (turn % RETRAIN_INTERVAL == 0):
            print(f"\n[ML] Running periodic training (turn {turn})...")
            try:
                res = ml_system.run_training_cycle()
                print(f"[ML TRAIN] {res}")
            except Exception as e:
                print(f"[ML TRAIN ERROR] {e}")

        time.sleep(1)


async def simulation_instance(instance_id: int, max_turns: int = MAX_TURNS):
    # Async wrapper using same logic but non-blocking sleeps
    turn = 0
    while RUNNING and (turn < max_turns):
        turn += 1
        mode = random.choice(MODES)

        print(f"\n[Instance {instance_id}] ===== TURN {turn} | MODE: {mode} =====")

        user_prompt = f"""
You are a hostile power user.
Test all system features.
Force edge cases.
Switch modes.
Conversation:
{conversation[-10:]}
Continue.
"""

        user_msg = call_model(USER_MODEL, user_prompt)
        conversation.append(("USER", user_msg))

        program_prompt = f"""
You are Sovereign system.
Mode: {mode}
Respond strictly according to mode logic.

Conversation:
{conversation[-10:]}
"""

        similar_cases = memory.search(user_msg)
        if similar_cases:
            program_prompt += "\nRelevant Past Failures:\n"
            for case in similar_cases:
                program_prompt += case + "\n"

        if mode == "DARBAR":
            ministers, final = darbar_debate(program_prompt, call_model, PROGRAM_MODEL, dry_run=DRY_RUN)
            program_msg = final
            for i, m in enumerate(ministers):
                conversation.append((f"MINISTER_{i+1}", m))
        else:
            program_msg = call_model(PROGRAM_MODEL, program_prompt)
            conversation.append(("PROGRAM", program_msg))

        print("\n[PROGRAM LLM]\n")
        print(program_msg)

        combined_input = f"MODE: {mode}\nUSER: {user_msg}\nPROGRAM: {program_msg}\n"
        try:
            ml_result = ml_system.process_decision(user_input=combined_input)
        except Exception as e:
            ml_result = {"error": str(e)}

        print("\n[ML SYSTEM]\n")
        print(ml_result)

        _log_turn(f"{instance_id}-{turn}", mode, user_msg, program_msg, ml_result)

        failure = _detect_failure(ml_result)
        if failure:
            memory.add(f"{mode} | USER: {user_msg} | PROGRAM: {program_msg}")

        try:
            features = ml_result.get("for_training", {}).get("situation_features", {})
            reward = reward_function(mode, features)
            print(f"[REWARD] instance={instance_id} mode={mode} reward={reward}")
        except Exception:
            pass

        # non-blocking sleep
        await asyncio.sleep(0.5)


def main():
    if args.workers and args.workers > 1:
        print(f"Starting async run with {args.workers} workers")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [simulation_instance(i, max_turns=MAX_TURNS) for i in range(args.workers)]
        try:
            loop.run_until_complete(asyncio.gather(*tasks))
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    else:
        run_sync_instance(0, max_turns=MAX_TURNS)


if __name__ == "__main__":
    main()

