"""
High-Control Multi-Agent Terminal Orchestrator

Features:
- Per-call timeout guard (kills model process on timeout)
- Optional live streaming of model output
- Optional conversation logging to `conversation.log`
- Clean separators, turn numbers, graceful Ctrl-C handling

Run:
    python -m multi_agent_sim.terminal
    
Or via the launcher:
    python -m multi_agent_sim.run_terminal

Configuration (via env vars):
  USER_MODEL: ollama user model name (default: deepseek-r1:8b)
  PROGRAM_MODEL: ollama program model name (default: qwen3:14b)
  MAX_TURNS: number of turns to run (default: 15)
  PER_CALL_TIMEOUT: seconds to wait for each model call (default: 30)
  STREAMING: if True, stream model output line-by-line (default: False)
  LOG_CONVERSATION: if True, append turns to `conversation.log` (default: False)

Note: Requires `ollama` CLI available in PATH and models installed.
"""

import subprocess
import time
import sys
import os
import shutil
import threading
from datetime import datetime

# ---------------------------
# Configuration
# ---------------------------
USER_MODEL = os.getenv("USER_MODEL", "deepseek-r1:8b")
PROGRAM_MODEL = os.getenv("PROGRAM_MODEL", "qwen3:14b")
MAX_TURNS = 15
PER_CALL_TIMEOUT = 30  # seconds per model call (timeout guard)
STREAMING = False      # attempt to stream model output line-by-line
LOG_CONVERSATION = False
LOG_PATH = "conversation.log"

# ---------------------------
# Utilities
# ---------------------------

def check_ollama_available():
    if shutil.which("ollama") is None:
        print("[WARN] `ollama` CLI not found in PATH. Install or add to PATH before running.")
        return False
    return True


def call_model(model, prompt, timeout=PER_CALL_TIMEOUT, streaming=STREAMING):
    """
    Call `ollama run <model>` with the given prompt.

    - Uses a timeout guard and kills process if it exceeds timeout.
    - If streaming=True, attempts to print stdout lines as they arrive.
    - Returns a tuple (output_text, had_timeout, stderr_text).
    """
    cmd = ["ollama", "run", model]

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        return (f"[ERROR] ollama not found when invoking model {model}", False, "ollama not found")
    except Exception as e:
        return (f"[ERROR] Failed to start model process: {e}", False, str(e))

    had_timeout = False
    stdout_collected = []
    stderr_collected = []

    try:
        if streaming:
            # Write prompt then stream stdout until process finishes or timeout
            try:
                proc.stdin.write(prompt)
                proc.stdin.close()
            except Exception:
                pass

            start = time.monotonic()
            while True:
                line = proc.stdout.readline()
                if line:
                    print(line.rstrip())
                    stdout_collected.append(line)
                if proc.poll() is not None:
                    # drain remaining
                    remaining = proc.stdout.read()
                    if remaining:
                        print(remaining.rstrip())
                        stdout_collected.append(remaining)
                    break
                # timeout check
                if time.monotonic() - start > timeout:
                    had_timeout = True
                    proc.kill()
                    break
                time.sleep(0.01)

            # capture stderr
            try:
                stderr_collected.append(proc.stderr.read())
            except Exception:
                pass

        else:
            # Non-streaming: communicate with timeout
            try:
                out, err = proc.communicate(prompt, timeout=timeout)
                stdout_collected.append(out or "")
                stderr_collected.append(err or "")
            except subprocess.TimeoutExpired:
                had_timeout = True
                try:
                    proc.kill()
                except Exception:
                    pass
                # attempt to read whatever is available
                try:
                    out, err = proc.communicate(timeout=5)
                    stdout_collected.append(out or "")
                    stderr_collected.append(err or "")
                except Exception:
                    pass

    except KeyboardInterrupt:
        try:
            proc.kill()
        except Exception:
            pass
        raise
    finally:
        # Ensure file descriptors closed
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        try:
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass

    output_text = "".join(stdout_collected).strip()
    stderr_text = "".join(stderr_collected).strip()

    if had_timeout:
        if not output_text:
            output_text = f"[TIMEOUT after {timeout}s]"
        else:
            output_text = output_text + f"\n[TIMEOUT after {timeout}s]"

    return (output_text, had_timeout, stderr_text)


# ---------------------------
# System prompts
# ---------------------------
user_system = """
You are a realistic human user.
You are curious, imperfect, sometimes unclear.
Start interacting with the system naturally.
"""

program_system = """
You are a structured software system.
Respond logically.
Do not hallucinate.
Be precise and concise.
"""

# ---------------------------
# Main loop
# ---------------------------

def main():
    print("\n=== MULTI-AGENT TERMINAL SIMULATION STARTED ===\n")

    if not check_ollama_available():
        print("Run `ollama list` to confirm models are installed before running this script.")

    conversation = []
    user_prompt = user_system

    try:
        for turn in range(1, MAX_TURNS + 1):
            print(f"\n---------- TURN {turn} ----------")

            # USER SPEAKS
            print("\n[USER LLM]:")
            user_out, user_timed_out, user_err = call_model(USER_MODEL, user_prompt)
            print(user_out)
            conversation.append(("USER", user_out))

            # PROGRAM RESPONDS
            program_prompt = program_system + "\n\nConversation:\n"
            for role, msg in conversation:
                program_prompt += f"{role}: {msg}\n"
            program_prompt += "\nRespond:"

            print("\n[PROGRAM LLM]:")
            program_out, prog_timed_out, prog_err = call_model(PROGRAM_MODEL, program_prompt)
            print(program_out)
            conversation.append(("PROGRAM", program_out))

            # Optional logging
            if LOG_CONVERSATION:
                try:
                    with open(LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"\nTURN {turn} - {datetime.utcnow().isoformat()}\n")
                        f.write(f"USER: {user_out}\n")
                        f.write(f"PROGRAM: {program_out}\n")
                except Exception as e:
                    print(f"[WARN] Failed to write log: {e}")

            # PREP NEXT USER PROMPT
            user_prompt = user_system + "\n\nConversation:\n"
            for role, msg in conversation:
                user_prompt += f"{role}: {msg}\n"
            user_prompt += "\nContinue as the user:"

            # Small delay
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Simulation stopped by user (KeyboardInterrupt).")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
    finally:
        print("\n=== SIMULATION COMPLETE ===\n")


if __name__ == "__main__":
    main()
