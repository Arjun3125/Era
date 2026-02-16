"""
diagnostics.py
Runtime observer utilities to detect common runtime architecture bugs.
"""
from typing import Any, Dict, List, Tuple


class RuntimeObserver:
    """Collect simple metrics and emit alerts for suspicious patterns."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.habit_history: List[Tuple[str, float]] = []

    def trace_event(self, name: str, payload: Dict[str, Any]) -> None:
        self.events.append({"name": name, "payload": payload})

    def record_habit(self, action_name: str, strength: float) -> None:
        self.habit_history.append((action_name, float(strength)))

    def detect_runaway_habit(self, window: int = 5, slope_threshold: float = 0.05) -> List[str]:
        # look for actions whose habit strength has increased rapidly
        alerts: List[str] = []
        try:
            recent = self.habit_history[-(window * 10) :]
            by_action: Dict[str, List[float]] = {}
            for a, s in recent:
                by_action.setdefault(a, []).append(float(s))
            for a, seq in by_action.items():
                if len(seq) < 2:
                    continue
                slope = (seq[-1] - seq[0]) / max(1, len(seq))
                if slope >= slope_threshold:
                    alerts.append(a)
        except Exception:
            pass
        return alerts

    def detect_missing_brake(self, stn_activity_log: List[float], threshold: float = 0.1) -> bool:
        # if STN activity is consistently below threshold while conflict events increase, signal missing brake
        try:
            if not stn_activity_log:
                return False
            avg = sum(stn_activity_log[-20:]) / len(stn_activity_log[-20:])
            return avg < threshold
        except Exception:
            return False

    def summary(self) -> Dict[str, Any]:
        return {"events_logged": len(self.events), "habits_tracked": len(self.habit_history)}
