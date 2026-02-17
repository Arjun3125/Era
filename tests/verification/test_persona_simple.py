#!/usr/bin/env python
"""
Simplified test of persona main() with timeout and output monitoring
"""
import os
import sys
import time
import threading

os.environ['AUTOMATED_SIMULATION'] = '1'
os.environ['PERSONA_DEBUG'] = '1'

print("[TEST] Starting persona main test...", flush=True)
sys.stdout.flush()

try:
    from persona.main import main
    
    print("[TEST] Main imported, starting thread...", flush=True)
    sys.stdout.flush()
    
    output_lock = threading.Lock()
    
    def run_main():
        print("[THREAD] Main thread starting", flush=True)
        sys.stdout.flush()
        try:
            main()
        except KeyboardInterrupt:
            print("[THREAD] Interrupted", flush=True)
        except Exception as e:
            print(f"[THREAD] Exception: {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            print("[THREAD] Main thread ending", flush=True)
            sys.stdout.flush()
    
    thread = threading.Thread(target=run_main, daemon=False)
    thread.start()
    
    # Monitor for 120 seconds
    print("[TEST] Monitoring main thread for 120 seconds...", flush=True)
    sys.stdout.flush()
    
    for i in range(120):
        time.sleep(1)
        is_alive = thread.is_alive()
        if i % 10 == 0:  # Print every 10 seconds to reduce spam
            print(f"[MONITOR] {i+1}s: thread_alive={is_alive}", flush=True)
            sys.stdout.flush()
        
        if not is_alive:
            break
    
    if thread.is_alive():
        print("[TEST] Main exceeded 45s, still running (probably waiting on LLM)", flush=True)
        # Don't join with timeout to avoid hanging the test
    else:
        print("[TEST] Main completed within timeout", flush=True)
    
except Exception as e:
    print(f"[TEST] Test error: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("[TEST] Test complete", flush=True)
sys.stdout.flush()
