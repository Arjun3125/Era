"""Temperature scaling for confidence calibration."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


def _logit(p: float) -> float:
    p = max(1e-6, min(1.0 - 1e-6, float(p)))
    return math.log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class TemperatureCalibrator:
    temperature: float

    def calibrate(self, confidence: float) -> float:
        t = max(1e-3, float(self.temperature))
        logit = _logit(confidence)
        scaled = logit / t
        return max(0.0, min(1.0, _sigmoid(scaled)))

    def calibrate_many(self, confidences: Iterable[float]) -> List[float]:
        return [self.calibrate(conf) for conf in confidences]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"temperature": self.temperature}, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "TemperatureCalibrator":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(temperature=float(payload.get("temperature", 1.0)))


def fit_temperature(confidences: Iterable[float], labels: Iterable[int]) -> TemperatureCalibrator:
    conf_list = list(confidences)
    label_list = list(labels)
    if not conf_list:
        return TemperatureCalibrator(temperature=1.0)

    best_t = 1.0
    best_loss = float("inf")
    for t in _grid_temperatures():
        loss = _nll(conf_list, label_list, t)
        if loss < best_loss:
            best_loss = loss
            best_t = t
    return TemperatureCalibrator(temperature=best_t)


def _nll(confidences: List[float], labels: List[int], temperature: float) -> float:
    total = 0.0
    count = 0
    calibrator = TemperatureCalibrator(temperature=temperature)
    for conf, label in zip(confidences, labels):
        prob = calibrator.calibrate(conf)
        label_val = 1.0 if label else 0.0
        prob = max(1e-6, min(1.0 - 1e-6, prob))
        if label_val == 1.0:
            total -= math.log(prob)
        else:
            total -= math.log(1.0 - prob)
        count += 1
    return total / max(1, count)


def _grid_temperatures() -> List[float]:
    values = []
    for step in range(5, 51):  # 0.5 -> 5.0
        values.append(step / 10.0)
    return values
