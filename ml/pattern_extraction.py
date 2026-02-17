# ml/pattern_extraction.py
"""
Pattern Extraction: Identifies decision patterns and failure trends.
Feeds learning signals to system retraining modules.
"""

from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import json

class PatternExtractor:
    """Extract patterns from episodic memory for ML training."""
    
    def __init__(self, episodic_memory=None):
        self.episodic_memory = episodic_memory
        self.patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.pattern_stats: Dict[str, Dict[str, int]] = {}
    
    def extract_patterns(self, num_episodes: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract decision patterns from recent episodes.
        Returns patterns grouped by pattern type.
        """
        if not self.episodic_memory:
            return {}
        
        # Get recent episodes
        recent = self.episodic_memory.get_recent_episodes(num_episodes)
        
        if not recent:
            return {}
        
        # Extract various pattern types
        domain_patterns = self._extract_domain_patterns(recent)
        confidence_patterns = self._extract_confidence_patterns(recent)
        outcome_patterns = self._extract_outcome_patterns(recent)
        sequential_patterns = self._extract_sequential_patterns(recent)
        
        all_patterns = {
            "domain_patterns": domain_patterns,
            "confidence_patterns": confidence_patterns,
            "outcome_patterns": outcome_patterns,
            "sequential_patterns": sequential_patterns,
        }
        
        self.patterns = all_patterns
        self._compute_pattern_stats(all_patterns)
        
        return all_patterns
    
    def _extract_domain_patterns(self, episodes) -> List[Dict[str, Any]]:
        """Identify success/failure patterns by domain."""
        domain_outcomes = defaultdict(lambda: {"success": 0, "failure": 0, "partial": 0})
        
        for ep in episodes:
            domain = ep.domain or "general"
            outcome = ep.outcome or "unknown"
            if outcome in domain_outcomes[domain]:
                domain_outcomes[domain][outcome] += 1
        
        patterns = []
        for domain, outcomes in domain_outcomes.items():
            total = sum(outcomes.values())
            success_rate = outcomes.get("success", 0) / total if total > 0 else 0.0
            
            pattern = {
                "type": "domain_performance",
                "domain": domain,
                "success_rate": success_rate,
                "total_decisions": total,
                "outcomes": outcomes,
                "strength": "strong" if total >= 10 else "weak"
            }
            patterns.append(pattern)
        
        return patterns
    
    def _extract_confidence_patterns(self, episodes) -> List[Dict[str, Any]]:
        """Identify patterns in confidence-outcome relationships."""
        patterns = []
        
        confidence_buckets = defaultdict(lambda: {"success": 0, "failure": 0})
        
        for ep in episodes:
            if ep.confidence is None:
                continue
            
            # Bucket confidence into ranges
            if ep.confidence >= 0.8:
                bucket = "high_confidence"
            elif ep.confidence >= 0.5:
                bucket = "medium_confidence"
            else:
                bucket = "low_confidence"
            
            outcome = ep.outcome or "unknown"
            if outcome in ["success", "failure"]:
                confidence_buckets[bucket][outcome] += 1
        
        for bucket, outcomes in confidence_buckets.items():
            total = sum(outcomes.values())
            if total > 0:
                success_rate = outcomes.get("success", 0) / total
                
                pattern = {
                    "type": "confidence_calibration",
                    "confidence_level": bucket,
                    "success_rate": success_rate,
                    "sample_size": total,
                    "well_calibrated": abs(success_rate - float(bucket.split("_")[0] == "high")) < 0.2
                }
                patterns.append(pattern)
        
        return patterns
    
    def _extract_outcome_patterns(self, episodes) -> List[Dict[str, Any]]:
        """Identify outcome distribution patterns."""
        outcomes = defaultdict(int)
        regret_by_outcome = defaultdict(list)
        
        for ep in episodes:
            outcome = ep.outcome or "unknown"
            outcomes[outcome] += 1
            
            if ep.outcome in ["failure", "success"]:
                regret_by_outcome[ep.outcome].append(ep.regret_score or 0.0)
        
        patterns = []
        for outcome, count in outcomes.items():
            regret_scores = regret_by_outcome.get(outcome, [])
            avg_regret = sum(regret_scores) / len(regret_scores) if regret_scores else 0.0
            
            pattern = {
                "type": "outcome_distribution",
                "outcome": outcome,
                "frequency": count,
                "average_regret": avg_regret,
            }
            patterns.append(pattern)
        
        return patterns
    
    def _extract_sequential_patterns(self, episodes) -> List[Dict[str, Any]]:
        """Identify patterns in decision sequences."""
        patterns = []
        
        if len(episodes) < 3:
            return patterns
        
        # Look for success/failure streaks
        current_streak = None
        streak_length = 0
        streaks = []
        
        for ep in episodes:
            outcome = "success" if ep.outcome == "success" else "failure"
            
            if current_streak is None:
                current_streak = outcome
                streak_length = 1
            elif outcome == current_streak:
                streak_length += 1
            else:
                if streak_length >= 2:
                    streaks.append({"outcome": current_streak, "length": streak_length})
                current_streak = outcome
                streak_length = 1
        
        if streak_length >= 2:
            streaks.append({"outcome": current_streak, "length": streak_length})
        
        if streaks:
            pattern = {
                "type": "sequential_patterns",
                "streaks": streaks,
                "longest_success_streak": max((s["length"] for s in streaks if s["outcome"] == "success"), default=0),
                "longest_failure_streak": max((s["length"] for s in streaks if s["outcome"] == "failure"), default=0),
            }
            patterns.append(pattern)
        
        return patterns
    
    def _compute_pattern_stats(self, patterns: Dict[str, Any]):
        """Compute aggregate statistics about patterns."""
        stats = {}
        
        for pattern_type, pattern_list in patterns.items():
            stats[pattern_type] = {
                "count": len(pattern_list),
                "average_strength": self._avg_strength(pattern_list),
            }
        
        self.pattern_stats = stats
    
    def _avg_strength(self, patterns: List[Dict[str, Any]]) -> float:
        """Compute average pattern strength."""
        if not patterns:
            return 0.0
        
        strengths = []
        for p in patterns:
            if "success_rate" in p:
                strengths.append(p["success_rate"])
            elif "sample_size" in p:
                strengths.append(min(p["sample_size"] / 20, 1.0))
        
        return sum(strengths) / len(strengths) if strengths else 0.0
    
    def identify_weak_patterns(self, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Identify patterns that underperform."""
        weak = []
        
        if not self.patterns:
            return weak
        
        for pattern_type, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                if pattern_type == "domain_patterns" and pattern.get("success_rate", 1.0) < threshold:
                    weak.append({"type": pattern_type, "pattern": pattern})
                elif pattern_type == "confidence_calibration" and not pattern.get("well_calibrated", False):
                    weak.append({"type": pattern_type, "pattern": pattern})
        
        return weak
    
    def generate_learning_signals(self) -> Dict[str, Any]:
        """
        Generate learning signals for ML retraining.
        These signals indicate which areas need improvement.
        """
        signals = {
            "timestamp": datetime.utcnow().isoformat(),
            "weak_domains": [],
            "confidence_issues": [],
            "outcome_distribution": {},
            "sequential_risks": [],
        }
        
        weak_patterns = self.identify_weak_patterns()
        
        for weak in weak_patterns:
            pattern = weak["pattern"]
            
            if weak["type"] == "domain_patterns":
                signals["weak_domains"].append({
                    "domain": pattern.get("domain"),
                    "success_rate": pattern.get("success_rate"),
                    "sample_size": pattern.get("total_decisions")
                })
            
            elif weak["type"] == "confidence_calibration":
                signals["confidence_issues"].append({
                    "confidence_level": pattern.get("confidence_level"),
                    "actual_success_rate": pattern.get("success_rate"),
                })
        
        # Outcome distribution
        for pattern in self.patterns.get("outcome_distribution", []):
            signals["outcome_distribution"][pattern.get("outcome")] = pattern.get("frequency", 0)
        
        # Sequential risks (long failure streaks)
        for pattern in self.patterns.get("sequential_patterns", []):
            if pattern.get("longest_failure_streak", 0) >= 3:
                signals["sequential_risks"].append({
                    "type": "long_failure_streak",
                    "length": pattern.get("longest_failure_streak")
                })
        
        return signals
    
    def save_patterns(self, output_path: str = "ml/cache/extracted_patterns.json"):
        """Save extracted patterns to disk."""
        try:
            with open(output_path, 'w') as f:
                json.dump({
                    "patterns": {k: v for k, v in self.patterns.items()},
                    "stats": self.pattern_stats,
                    "timestamp": datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save patterns: {e}")
