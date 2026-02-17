#!/usr/bin/env python
import sys
import os

print("[TEST] Starting test...", flush=True)
sys.stdout.flush()

os.environ['AUTOMATED_SIMULATION'] = '1'
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
finally:
    print("[TEST] Test complete", flush=True)
