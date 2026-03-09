# Simple runner script to start the interactive persona
import os
import sys
from pathlib import Path

from adapters.legacy import LegacyEntrypointPlugin, run_legacy_entrypoint

print("[STARTUP] Loading environment...", file=sys.stderr, flush=True)

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


try:
    print("[STARTUP] Trying python-dotenv...", file=sys.stderr, flush=True)
    from dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    print(f"[STARTUP] Fallback to manual .env parsing...", file=sys.stderr, flush=True)
    _load_dotenv_fallback()

print(f"[STARTUP] AUTOMATED_SIMULATION={os.environ.get('AUTOMATED_SIMULATION')}", file=sys.stderr, flush=True)
print("[STARTUP] Importing persona.main...", file=sys.stderr, flush=True)

from persona.main import main

print("[STARTUP] Starting main()...", file=sys.stderr, flush=True)


def _run_via_orchestrator() -> int:
    """Execute legacy persona main through the central orchestrator wrapper."""
    plugin = LegacyEntrypointPlugin(plugin_name="persona.main", entrypoint=main)

    report = run_legacy_entrypoint(
        plugin=plugin,
        command_name="persona.run_persona",
        argv=list(sys.argv[1:]),
        metadata={"entrypoint": "persona/run_persona.py"},
    )

    if report.result.status.value == "aborted":
        first_error = (
            report.result.context.errors[0].message
            if report.result.context.errors
            else "unknown"
        )
        print(f"[STARTUP] Orchestration aborted: {first_error}", file=sys.stderr, flush=True)
        return 1

    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(_run_via_orchestrator())
