"""Adaptive rate controller stub."""

from __future__ import annotations


class AdaptiveRateController:
    def __init__(self, initial_concurrency: int = 5, min_concurrency: int = 1, max_concurrency: int = 20) -> None:
        self.concurrency = int(initial_concurrency)
        self.min_concurrency = int(min_concurrency)
        self.max_concurrency = int(max_concurrency)
        self.rate_limit_hits = 0
        self._latencies = []

    def record_success(self, latency: float) -> None:
        self._latencies.append(float(latency))

    def adjust(self) -> None:
        if self.rate_limit_hits > 0:
            self.concurrency = max(self.min_concurrency, self.concurrency - 1)
            self.rate_limit_hits = 0
            return
        if self._latencies and sum(self._latencies) / len(self._latencies) < 0.5:
            self.concurrency = min(self.max_concurrency, self.concurrency + 1)
