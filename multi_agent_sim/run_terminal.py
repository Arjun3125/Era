"""
Wrapper to auto-select two Ollama models and run the multi-agent terminal.

Usage:
  python -m multi_agent_sim.run_terminal              # runs and launches orchestrator
  python -m multi_agent_sim.run_terminal --dry-run    # prints detected models and exits

It sets env vars `USER_MODEL` and `PROGRAM_MODEL` for `terminal.py`.
"""
import os
import argparse
import subprocess
import sys
from pathlib import Path

# Add parent directory to path to import ollama_model_selector from llm
sys.path.insert(0, str(Path(__file__).parent.parent))
from llm.ollama_model_selector import select_models


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Only detect models and print them")
    parser.add_argument("--preferred", nargs="*", help="Preferred model prefixes, e.g. deepseek qwen")
    args = parser.parse_args()

    preferred = args.preferred if args.preferred else None
    user_model, program_model = select_models(preferred=preferred)

    if args.dry_run:
        print("Detected models:")
        print(" USER_MODEL:", user_model)
        print(" PROGRAM_MODEL:", program_model)
        if not user_model:
            print("[WARN] No ollama CLI or no models installed. Run `ollama list` to confirm.")
        return 0

    if not user_model:
        print("[ERROR] No Ollama models detected. Aborting.")
        print("Run `ollama list` and install models, or run with USER_MODEL/PROGRAM_MODEL env vars.")
        return 2

    env = os.environ.copy()
    env["USER_MODEL"] = user_model
    if program_model:
        env["PROGRAM_MODEL"] = program_model

    # Get path to terminal.py in this package
    terminal_path = Path(__file__).parent / "terminal.py"
    print(f"Launching multi-agent terminal with USER_MODEL={user_model} PROGRAM_MODEL={program_model}")
    # Launch the terminal script in a subprocess
    try:
        proc = subprocess.Popen([sys.executable, str(terminal_path)], env=env)
        proc.wait()
        return proc.returncode
    except KeyboardInterrupt:
        print("Interrupted by user")
        return 1
    except Exception as e:
        print("Failed to launch terminal:", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
