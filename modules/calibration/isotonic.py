"""Isotonic regression calibration for predicted probabilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import joblib
from sklearn.isotonic import IsotonicRegression


@dataclass
class IsotonicCalibrator:
    model: IsotonicRegression | None = None

    def fit(self, probabilities: Iterable[float], labels: Iterable[int]) -> None:
        probs = [float(value) for value in probabilities]
        targets = [int(value) for value in labels]
        self.model = IsotonicRegression(out_of_bounds="clip")
        self.model.fit(probs, targets)

    def predict(self, probabilities: Iterable[float]) -> List[float]:
        if self.model is None:
            raise RuntimeError("IsotonicCalibrator has not been fitted.")
        values = [float(value) for value in probabilities]
        return [float(value) for value in self.model.predict(values)]

    def save(self, path: Path) -> None:
        if self.model is None:
            raise RuntimeError("IsotonicCalibrator has not been fitted.")
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)

    @classmethod
    def load(cls, path: Path) -> "IsotonicCalibrator":
        model = joblib.load(path)
        return cls(model=model)
