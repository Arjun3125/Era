"""Composition helper for probability calibration steps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from modules.uncertainty.calibration import TemperatureCalibrator

from .isotonic import IsotonicCalibrator


@dataclass
class ProbabilityCalibrator:
    temperature: Optional[TemperatureCalibrator] = None
    isotonic: Optional[IsotonicCalibrator] = None

    def calibrate(self, probability: float) -> float:
        value = float(probability)
        if self.temperature is not None:
            value = self.temperature.calibrate(value)
        if self.isotonic is not None:
            value = self.isotonic.predict([value])[0]
        return max(0.0, min(1.0, float(value)))

    @classmethod
    def from_paths(
        cls,
        temperature_path: Optional[Path],
        isotonic_path: Optional[Path],
    ) -> "ProbabilityCalibrator | None":
        temperature = None
        isotonic = None
        if temperature_path:
            temperature = TemperatureCalibrator.load(temperature_path)
        if isotonic_path:
            isotonic = IsotonicCalibrator.load(isotonic_path)
        if temperature is None and isotonic is None:
            return None
        return cls(temperature=temperature, isotonic=isotonic)
