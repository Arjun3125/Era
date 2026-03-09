#!/usr/bin/env python3
"""Compatibility entrypoint that delegates to the refactored pipeline runtime."""

from __future__ import annotations

from run_refactored import main as run_refactored_main


def main() -> int:
    """Execute the refactored runtime while preserving `python system_main.py`."""
    return int(run_refactored_main())


if __name__ == "__main__":
    raise SystemExit(main())
