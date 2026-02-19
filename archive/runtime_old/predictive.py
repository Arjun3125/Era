"""
predictive.py
Simple PredictionEngine to compute predictions and prediction errors.
"""
from typing import Any, Callable, Dict, List


class PredictionEngine:
    """Lightweight predictive-processing engine.

    Usage:
        engine = PredictionEngine(model_fn)
        pred = engine.predict(state)
        err = engine.update(actual_state)
    """

    def __init__(self, model_fn: Callable[[Dict[str, Any]], Dict[str, Any]] | None = None):
        # model_fn(state) -> predicted_state
        self.model_fn = model_fn or (lambda s: s.copy() if isinstance(s, dict) else s)
        self.last_prediction = None
        self.listeners: List[Callable[[float, Dict[str, Any], Dict[str, Any]], None]] = []

    def predict(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pred = self.model_fn(state)
        self.last_prediction = pred
        return pred

    def update(self, actual: Dict[str, Any]) -> float:
        """Compute simple L1 prediction error between last_prediction and actual.
        Notify listeners with (error, prediction, actual).
        Returns error magnitude.
        """
        if self.last_prediction is None:
            return 0.0
        pred = self.last_prediction
        # flatten numeric fields where possible
        err = 0.0
        try:
            for k, v in actual.items():
                pv = pred.get(k) if isinstance(pred, dict) else None
                try:
                    if pv is None:
                        continue
                    err += abs(float(v) - float(pv))
                except Exception:
                    # non-numeric fields count as mismatch 0/1
                    if pv != v:
                        err += 1.0
        except Exception:
            err = 0.0

        for cb in self.listeners:
            try:
                cb(err, pred, actual)
            except Exception:
                pass
        return float(err)

    def add_listener(self, cb: Callable[[float, Dict[str, Any], Dict[str, Any]], None]) -> None:
        self.listeners.append(cb)

    def clear_listeners(self) -> None:
        self.listeners.clear()
