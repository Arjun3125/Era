"""
consciousness.py
Model for a broadcasting threshold: decides whether a signal reaches conscious access.
"""
from typing import Dict, Any


class ConsciousnessThreshold:
    """Simple threshold model. If signal strength exceeds threshold -> conscious.

    Methods:
      - is_conscious(signal_strength, attention_bias=0.0)
    """

    def __init__(self, threshold: float = 1.0):
        self.threshold = float(threshold)

    def is_conscious(self, signal_strength: float, attention_bias: float = 0.0) -> bool:
        try:
            strength = float(signal_strength) + float(attention_bias)
        except Exception:
            strength = float(signal_strength)
        return strength >= self.threshold

    def adjust_threshold(self, delta: float) -> None:
        self.threshold = max(0.0, self.threshold + float(delta))
