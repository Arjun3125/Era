"""
dopamine.py
Simple learning signal utilities implementing temporal-difference style update.
"""
from typing import Any


class LearningSignal:
    """Compute weight updates from prediction error.

    delta_weight = lr * prediction_error * activity
    """

    def __init__(self, learning_rate: float = 0.1):
        self.learning_rate = float(learning_rate)

    def compute_delta(self, prediction_error: float, activity: float) -> float:
        try:
            pe = float(prediction_error)
            act = float(activity)
        except Exception:
            pe = 0.0
            act = 0.0
        return self.learning_rate * pe * act

    def apply_update(self, weight: float, prediction_error: float, activity: float) -> float:
        delta = self.compute_delta(prediction_error, activity)
        return float(weight + delta)
