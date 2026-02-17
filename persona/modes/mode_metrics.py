"""
Mode-specific metrics tracking.

Measure how well Persona performs in each mode:
- QUICK mode: Fast, intuitive decisions
- WAR mode: Victory-focused strategic decisions  
- MEETING mode: Balanced, consensus-seeking decisions
- DARBAR mode: Full wisdom, doctrine-respecting decisions

Tracks:
- Decision count per mode
- Success/failure rates per mode
- Average confidence per mode
- Average regret/learning per mode

Usage:
    metrics = ModeMetrics()
    metrics.record_mode_decision("war", "success", confidence=0.85, regret=0.1)
    perf = metrics.get_mode_performance("war")
    comparison = metrics.compare_modes()
"""

from typing import Dict, List
from collections import defaultdict


class ModeMetrics:
    """
    Track performance metrics by decision mode.
    
    Enables analysis of which modes work best for different situations
    and identifies mode-specific strengths/weaknesses.
    """
    
    def __init__(self):
        """Initialize empty metrics storage."""
        self.by_mode = defaultdict(lambda: {
            "turns": 0,
            "successes": 0,
            "failures": 0,
            "avg_confidence": 0.0,
            "avg_regret": 0.0,
            "total_decisions": 0,
        })
    
    def record_mode_decision(
        self,
        mode: str,
        outcome: str,
        confidence: float,
        regret: float = 0.0
    ) -> None:
        """
        Record a decision outcome for a specific mode.
        
        Args:
            mode: Decision mode ("quick", "war", "meeting", "darbar")
            outcome: Decision outcome ("success", "failure", or "neutral")
            confidence: Confidence level (0.0-1.0)
            regret: Regret score (0.0-1.0, higher = more regrettable)
        """
        stats = self.by_mode[mode]
        stats["turns"] += 1
        stats["total_decisions"] += 1
        
        # Track outcomes
        if outcome == "success":
            stats["successes"] += 1
        elif outcome == "failure":
            stats["failures"] += 1
        
        # Update running averages
        total = stats["successes"] + stats["failures"]
        if total > 0:
            # Recalculate average confidence
            old_avg = stats["avg_confidence"]
            stats["avg_confidence"] = (
                (old_avg * (total - 1) + confidence) / total
            )
            
            # Recalculate average regret
            old_regret = stats["avg_regret"]
            stats["avg_regret"] = (
                (old_regret * (total - 1) + regret) / total
            )
    
    def get_mode_performance(self, mode: str) -> Dict[str, float]:
        """
        Get performance statistics for a specific mode.
        
        Args:
            mode: Decision mode to query
            
        Returns:
            Dict with keys:
                - mode: Mode name
                - turns: Total decisions in this mode
                - success_rate: Proportion of successful decisions (0.0-1.0)
                - failure_rate: Proportion of failed decisions (0.0-1.0)
                - avg_confidence: Average confidence across decisions
                - avg_regret: Average regret across decisions
        """
        stats = self.by_mode[mode]
        total = stats["successes"] + stats["failures"]
        
        if total == 0:
            return {
                "mode": mode,
                "turns": 0,
                "success_rate": 0.0,
                "failure_rate": 0.0,
                "avg_confidence": 0.0,
                "avg_regret": 0.0,
            }
        
        return {
            "mode": mode,
            "turns": stats["turns"],
            "total_decisions": total,
            "success_rate": stats["successes"] / total,
            "failure_rate": stats["failures"] / total,
            "avg_confidence": stats["avg_confidence"],
            "avg_regret": stats["avg_regret"],
        }
    
    def compare_modes(self) -> List[Dict[str, float]]:
        """
        Compare performance across all modes.
        
        Returns:
            List of performance dicts for all modes, sorted by success rate (descending)
        """
        results = [self.get_mode_performance(mode) for mode in self.by_mode.keys()]
        # Sort by success rate (descending)
        return sorted(results, key=lambda x: x.get("success_rate", 0.0), reverse=True)
    
    def get_best_mode(self) -> Dict[str, float]:
        """
        Get the mode with highest success rate.
        
        Returns:
            Performance dict for the best-performing mode
        """
        comparison = self.compare_modes()
        return comparison[0] if comparison else {}
    
    def get_worst_mode(self) -> Dict[str, float]:
        """
        Get the mode with lowest success rate.
        
        Returns:
            Performance dict for the worst-performing mode
        """
        comparison = self.compare_modes()
        return comparison[-1] if comparison else {}
    
    def get_mode_summary(self) -> Dict[str, Dict]:
        """
        Get summary stats for all modes.
        
        Returns:
            Dict mapping mode name to performance dict
        """
        return {mode: self.get_mode_performance(mode) for mode in self.by_mode.keys()}
    
    def reset_mode(self, mode: str) -> None:
        """
        Reset metrics for a specific mode.
        
        Args:
            mode: Mode to reset
        """
        self.by_mode[mode] = {
            "turns": 0,
            "successes": 0,
            "failures": 0,
            "avg_confidence": 0.0,
            "avg_regret": 0.0,
            "total_decisions": 0,
        }
    
    def reset_all(self) -> None:
        """Reset all metrics."""
        self.by_mode.clear()
    
    def get_all_modes(self) -> List[str]:
        """Get list of all modes with recorded data."""
        return list(self.by_mode.keys())
    
    def has_data_for_mode(self, mode: str) -> bool:
        """Check if metrics exist for a mode."""
        return mode in self.by_mode and self.by_mode[mode]["total_decisions"] > 0
