#!/usr/bin/env python
import sys
import os
import pytest

if "pytest" in sys.modules:
    if not os.getenv("ERA_RUN_INTEGRATION_TESTS"):
        pytest.skip(
            "integration test; set ERA_RUN_INTEGRATION_TESTS=1 to run",
            allow_module_level=True,
        )
    if not os.getenv("ERA_RUN_INTERACTIVE_TESTS"):
        pytest.skip(
            "interactive test; set ERA_RUN_INTERACTIVE_TESTS=1 to run",
            allow_module_level=True,
        )

def test_persona_startup():
    print("[TEST] Starting test...", flush=True)
    sys.stdout.flush()

    os.environ['AUTOMATED_SIMULATION'] = '1'
    os.environ['ERA_AUTOMATED_MAX_TURNS'] = '3'
    print("[TEST] Env set to AUTOMATED_SIMULATION=1", flush=True)
    sys.stdout.flush()

    try:
        print("[TEST] Importing persona.main...", flush=True)
        sys.stdout.flush()
        from persona.main import main
        print("[TEST] Import successful, calling main()...", flush=True)
        sys.stdout.flush()
        main()
    except KeyboardInterrupt:
        print("\n[TEST] Interrupted by user", flush=True)
    except Exception as e:
        print(f"[TEST] Error: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("[TEST] Test complete", flush=True)
