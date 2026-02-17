# persona/learning/performance_metrics.py
"""
Performance Metrics: Track decision quality, success rates, feature coverage.
Identifies weak domains and improvement opportunities.
"""

import json
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime

class PerformanceMetrics:
    def __init__(self, storage_path: str = "data/memory/metrics.jsonl"):
        self.storage_path = storage_path
        self.decisions: List[Dict[str, Any]] = []
        self.load_from_disk()
    
    def record_decision(self, turn: int, domain: str, recommendation: str, 
                       confidence: float, outcome: str = None, regret: float = 0.0):
        """Record a decision for metrics tracking."""
        decision = {
            "turn": turn,
            "domain": domain,
            "recommendation": recommendation,
            "confidence": confidence,
            "outcome": outcome,
            "regret": regret,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.decisions.append(decision)
        self._persist(decision)
    
    def _persist(self, decision: Dict[str, Any]):
        """Append to disk."""
        try:
            with open(self.storage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(decision) + "\n")
        except Exception as e:
            print(f"[WARNING] Failed to persist metric: {e}")
    
    def load_from_disk(self):
        """Load metrics from disk."""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        self.decisions.append(json.loads(line))
        except FileNotFoundError:
            pass
    
    def get_success_rate(self, domain: str = None, window: int = None) -> float:
        """Success rate overall or for domain."""
        decisions = self.decisions
        if domain:
            decisions = [d for d in decisions if d.get("domain") == domain]
        if window:
            decisions = decisions[-window:]
        
        if not decisions:
            return 0.0
        
        outcomes = [d for d in decisions if d.get("outcome")]
        if not outcomes:
            return 0.0
        
        successes = sum(1 for d in outcomes if d.get("outcome") == "success")
        return successes / len(outcomes)
    
    def get_feature_coverage(self) -> Dict[str, int]:
        """How many times each domain was tested?"""
        coverage = defaultdict(int)
        for d in self.decisions:
            coverage[d.get("domain", "unknown")] += 1
        return dict(coverage)
    
    def detect_weak_domains(self, threshold: float = 0.5) -> List[str]:
        """Which domains are underperforming?"""
        weak = []
        coverage = self.get_feature_coverage()
        for domain in coverage:
            success_rate = self.get_success_rate(domain=domain)
            if success_rate < threshold:
                weak.append(domain)
        return weak
    
    def measure_stability(self, window: int = 100) -> Dict[str, Any]:
        """Check if recent decisions are consistent."""
        recent = self.decisions[-window:]
        if not recent:
            return {"stability_score": 0.0}
        
        # Consistency: low variance in confidence across domain
        by_domain = defaultdict(list)
        for d in recent:
            by_domain[d.get("domain")].append(d.get("confidence", 0.0))
        
        # Calculate variance per domain
        variances = {}
        for domain, confidences in by_domain.items():
            if len(confidences) > 1:
                mean = sum(confidences) / len(confidences)
                variance = sum((x - mean) ** 2 for x in confidences) / len(confidences)
                variances[domain] = variance
        
        # Stability = inverse of mean variance (lower variance = more stable)
        mean_variance = sum(variances.values()) / len(variances) if variances else 0.0
        stability_score = max(0.0, 1.0 - mean_variance)
        
        return {
            "stability_score": stability_score,
            "by_domain": variances
        }
    
    def show_improvement_trajectory(self, window: int = 100) -> Dict[str, Any]:
        """Compare early vs. recent performance."""
        total = len(self.decisions)
        early = self.decisions[:window]
        recent = self.decisions[-window:]
        
        early_success = sum(1 for d in early if d.get("outcome") == "success") / max(len(early), 1)
        recent_success = sum(1 for d in recent if d.get("outcome") == "success") / max(len(recent), 1)
        
        improvement = recent_success - early_success
        improvement_pct = (improvement / early_success * 100) if early_success > 0 else 0.0
        
        return {
            "early_success_rate": early_success,
            "recent_success_rate": recent_success,
            "absolute_improvement": improvement,
            "percent_improvement": improvement_pct,
            "total_turns": total
        }
