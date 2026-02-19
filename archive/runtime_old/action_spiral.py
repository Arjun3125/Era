"""
action_spiral.py
Simple ActionSelection simulating valuation -> goal-directed -> habitual handoff.
"""
from typing import Dict, Any, List, Tuple


class ActionSelection:
    """Model action selection with habit override.

    - actions: dict[action_name] -> dict with keys `value`, `habit_strength`
    - select_action returns action name and reason
    """

    def __init__(self, habit_threshold: float = 0.8):
        self.habit_threshold = habit_threshold

    def select_action(self, actions: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
        # If any habit_strength exceeds threshold, pick that habit
        best_habit = None
        best_habit_strength = 0.0
        for name, info in actions.items():
            hs = float(info.get("habit_strength", 0.0) or 0.0)
            if hs > best_habit_strength:
                best_habit_strength = hs
                best_habit = name
        if best_habit is not None and best_habit_strength >= self.habit_threshold:
            return best_habit, "habit"

        # otherwise pick highest value
        best_act = None
        best_val = float("-inf")
        for name, info in actions.items():
            val = float(info.get("value", 0.0) or 0.0)
            if val > best_val:
                best_val = val
                best_act = name
        return best_act or "none", "goal-directed"

    def reinforce_habit(self, actions: Dict[str, Dict[str, Any]], action_name: str, reward: float, lr: float = 0.1) -> None:
        info = actions.get(action_name)
        if not info:
            return
        hs = float(info.get("habit_strength", 0.0) or 0.0)
        hs = hs + lr * float(reward)
        info["habit_strength"] = min(1.0, max(0.0, hs))
