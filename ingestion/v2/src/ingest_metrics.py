"""Metrics collection and reporting for async ingestion pipeline."""
from collections import deque
from dataclasses import dataclass, field
from typing import Dict
import time


@dataclass
class IngestMetrics:
    """Collects and reports per-stage metrics."""
    
    embed_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    db_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    minister_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    processed: int = 0
    dropped: int = 0
    rate_limit_hits: int = 0
    errors: int = 0
    
    start_time: float = field(default_factory=time.time)
    last_report_time: float = field(default_factory=time.time)

    def record_embed(self, latency: float):
        """Record embedding call latency."""
        self.embed_times.append(latency)

    def record_db(self, latency: float):
        """Record DB write latency."""
        self.db_times.append(latency)

    def record_minister(self, latency: float):
        """Record minister aggregation latency."""
        self.minister_times.append(latency)

    def record_processed(self, count: int = 1):
        """Increment processed count."""
        self.processed += count

    def record_dropped(self, count: int = 1):
        """Increment dropped count."""
        self.dropped += count

    def record_rate_limit(self):
        """Increment rate limit hit counter."""
        self.rate_limit_hits += 1

    def record_error(self):
        """Increment error counter."""
        self.errors += 1

    def get_throughput(self) -> float:
        """Get throughput in chunks/sec."""
        elapsed = time.time() - self.start_time
        return self.processed / max(1, elapsed)

    def get_avg_embed_latency(self) -> float:
        """Get average embedding latency."""
        if not self.embed_times:
            return 0.0
        return sum(self.embed_times) / len(self.embed_times)

    def get_avg_db_latency(self) -> float:
        """Get average DB write latency."""
        if not self.db_times:
            return 0.0
        return sum(self.db_times) / len(self.db_times)

    def get_avg_minister_latency(self) -> float:
        """Get average minister aggregation latency."""
        if not self.minister_times:
            return 0.0
        return sum(self.minister_times) / len(self.minister_times)

    def report(self) -> Dict[str, float]:
        """Generate comprehensive metrics report."""
        elapsed = time.time() - self.start_time
        
        report = {
            "elapsed_seconds": elapsed,
            "processed_chunks": self.processed,
            "dropped_chunks": self.dropped,
            "rate_limit_hits": self.rate_limit_hits,
            "errors": self.errors,
            "throughput_chunks_per_sec": self.get_throughput(),
            "avg_embed_latency_ms": self.get_avg_embed_latency() * 1000,
            "avg_db_latency_ms": self.get_avg_db_latency() * 1000,
            "avg_minister_latency_ms": self.get_avg_minister_latency() * 1000,
        }
        
        self.last_report_time = time.time()
        return report

    @property
    def processed_chunks(self) -> int:
        """Compatibility alias for older code referencing processed_chunks."""
        return self.processed

    def print_report(self):
        """Print a formatted metrics report."""
        report = self.report()
        print("\n" + "=" * 70)
        print("INGESTION METRICS REPORT")
        print("=" * 70)
        for key, value in report.items():
            if isinstance(value, float):
                print(f"  {key:.<50} {value:.2f}")
            else:
                print(f"  {key:.<50} {value}")
        print("=" * 70 + "\n")


__all__ = ["IngestMetrics"]
