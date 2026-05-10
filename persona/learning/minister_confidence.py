"""Bayesian per-minister confidence calibration."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional


@dataclass
class _MinisterRecord:
    successes: float = 0.0
    failures: float = 0.0


class MinisterConfidenceTracker:
    """Track per-minister, per-domain outcome history and compute confidence weights.

    Prior: alpha=2 successes, beta=2 failures (neutral start at 0.5).
    Weight = (alpha + successes) / (alpha + beta + successes + failures) / prior_mean.
    """

    _ALPHA = 2.0  # prior successes
    _BETA = 2.0   # prior failures
    _PRIOR_MEAN = _ALPHA / (_ALPHA + _BETA)  # 0.5

    def __init__(self, storage_path: str = ":memory:"):
        self.storage_path = storage_path
        self._records: Dict[str, _MinisterRecord] = {}
        self._load()

    def _key(self, minister: str, domain: str) -> str:
        return f"{minister}::{domain}"

    def _load(self) -> None:
        if self.storage_path == ":memory:":
            return
        p = Path(self.storage_path)
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for k, v in data.items():
                self._records[k] = _MinisterRecord(**v)
        except Exception:
            pass

    def _save(self) -> None:
        if self.storage_path == ":memory:":
            return
        p = Path(self.storage_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            p.write_text(
                json.dumps({k: asdict(v) for k, v in self._records.items()}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def record_outcome(self, minister: str, domain: str, success: bool) -> None:
        """Increment success or failure count for a minister/domain pair."""
        key = self._key(minister, domain)
        if key not in self._records:
            self._records[key] = _MinisterRecord()
        if success:
            self._records[key].successes += 1.0
        else:
            self._records[key].failures += 1.0
        self._save()

    def get_weight(self, minister: str, domain: str) -> float:
        """Return Bayesian weight: > 1.0 after consistent success, < 1.0 after failures."""
        key = self._key(minister, domain)
        rec = self._records.get(key, _MinisterRecord())
        posterior_mean = (self._ALPHA + rec.successes) / (
            self._ALPHA + self._BETA + rec.successes + rec.failures
        )
        weight = posterior_mean / self._PRIOR_MEAN
        return round(max(0.01, weight), 4)
