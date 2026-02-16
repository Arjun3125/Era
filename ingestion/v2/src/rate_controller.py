"""Adaptive rate limiting controller for LLM embedding calls."""
import asyncio
from typing import Optional
from .async_ingest_config import (
    MAX_EMBED_CONCURRENCY,
    MAX_EMBED_CONCURRENCY_MIN,
    MAX_EMBED_CONCURRENCY_MAX,
    RATE_LIMIT_ADJUSTMENT_THRESHOLD,
    LATENCY_WINDOW_SIZE,
    LATENCY_LOWER_THRESHOLD,
    LATENCY_UPPER_THRESHOLD,
)


class AdaptiveRateController:
    """Dynamically adjusts concurrency and batch size based on API feedback."""

    def __init__(
        self,
        initial_concurrency: int = MAX_EMBED_CONCURRENCY,
        max_concurrency: int = MAX_EMBED_CONCURRENCY_MAX,
        min_concurrency: int = MAX_EMBED_CONCURRENCY_MIN,
    ):
        self.initial_concurrency = initial_concurrency
        self.concurrency = initial_concurrency
        self.max_concurrency = max_concurrency
        self.min_concurrency = min_concurrency

        self.success_count = 0
        self.rate_limit_hits = 0
        self.latencies = []
        
        # Semaphore for rate limiting
        self._semaphore = asyncio.Semaphore(self.concurrency)

    def record_success(self, latency: float):
        """Record a successful API call."""
        self.success_count += 1
        self.latencies.append(latency)

    def record_rate_limit(self):
        """Record a rate-limit error (429)."""
        self.rate_limit_hits += 1

    def record_error(self):
        """Record a generic error."""
        pass

    async def acquire(self):
        """Acquire a slot in the semaphore."""
        await self._semaphore.acquire()

    def release(self):
        """Release a semaphore slot."""
        self._semaphore.release()

    def adjust(self):
        """Adjust concurrency based on observed behavior."""
        
        # If we hit rate limits, back off aggressively
        if self.rate_limit_hits >= RATE_LIMIT_ADJUSTMENT_THRESHOLD:
            old_concurrency = self.concurrency
            self.concurrency = max(
                self.min_concurrency,
                int(self.concurrency * 0.7)
            )
            print(
                f"[RateController] Rate limit detected ({self.rate_limit_hits} hits). "
                f"Reduced concurrency: {old_concurrency} -> {self.concurrency}"
            )
            self.rate_limit_hits = 0
            self.latencies.clear()
            self._update_semaphore()
            return

        # If latencies are low, we can increase concurrency
        if len(self.latencies) >= LATENCY_WINDOW_SIZE:
            avg_latency = sum(self.latencies) / len(self.latencies)

            if avg_latency < LATENCY_LOWER_THRESHOLD:
                old_concurrency = self.concurrency
                self.concurrency = min(
                    self.max_concurrency,
                    self.concurrency + 2
                )
                print(
                    f"[RateController] Low latency ({avg_latency:.3f}s). "
                    f"Increased concurrency: {old_concurrency} -> {self.concurrency}"
                )
                self._update_semaphore()

            elif avg_latency > LATENCY_UPPER_THRESHOLD:
                old_concurrency = self.concurrency
                self.concurrency = max(
                    self.min_concurrency,
                    int(self.concurrency * 0.9)
                )
                print(
                    f"[RateController] High latency ({avg_latency:.3f}s). "
                    f"Reduced concurrency: {old_concurrency} -> {self.concurrency}"
                )
                self._update_semaphore()

            self.latencies.clear()

    def _update_semaphore(self):
        """Update the semaphore to reflect new concurrency limit."""
        # Create a new semaphore with updated capacity
        self._semaphore = asyncio.Semaphore(self.concurrency)

    async def sleep_backoff(self, attempt: int = 1):
        """Exponential backoff sleep (for rate limit recovery)."""
        await asyncio.sleep(min(2 ** attempt, 32))  # Cap at 32 seconds

    def get_status(self) -> dict:
        """Get current controller status."""
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        return {
            "current_concurrency": self.concurrency,
            "success_count": self.success_count,
            "rate_limit_hits": self.rate_limit_hits,
            "avg_latency": avg_latency,
            "latency_window": len(self.latencies),
        }


__all__ = ["AdaptiveRateController"]
