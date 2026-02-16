"""Entry point for running multi_agent_sim as a module.

Usage:
  python -m multi_agent_sim.terminal          # run terminal directly
  python -m multi_agent_sim.run_terminal      # run with auto model selection
  python -m multi_agent_sim.demo              # run demo simulation
"""
import sys
from . import terminal, run_terminal, demo


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    
    cmd = sys.argv[1]
    
    if cmd == "terminal":
        return terminal.main() if hasattr(terminal, "main") else 0
    elif cmd == "run" or cmd == "run_terminal":
        return run_terminal.main()
    elif cmd == "demo":
        return demo.main() if hasattr(demo, "main") else 0
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
