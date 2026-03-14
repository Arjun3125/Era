"""Model selection stub."""

from __future__ import annotations

from typing import Iterable, Tuple


def select_models(preferred: Iterable[str] | None = None) -> Tuple[str, str]:
    options = list(preferred or [])
    primary = options[0] if options else "mock-model"
    return primary, primary
