from __future__ import annotations

from pathlib import Path

import pytest

from modules.calibration.calibrator import ProbabilityCalibrator
from modules.calibration.isotonic import IsotonicCalibrator
from modules.uncertainty.calibration import TemperatureCalibrator, fit_temperature
from modules.uncertainty.metrics import (
    calibration_bins,
    brier_score,
    expected_calibration_error,
)
from modules.uncertainty.reliability_plot import plot_reliability_curve
from modules.uncertainty.risk_model import RiskModel


def test_temperature_calibrator_round_trip(tmp_path: Path) -> None:
    calibrator = TemperatureCalibrator(temperature=2.0)
    values = calibrator.calibrate_many([0.2, 0.8])
    assert all(0.0 <= value <= 1.0 for value in values)

    path = tmp_path / "calibration" / "temperature.json"
    calibrator.save(path)
    loaded = TemperatureCalibrator.load(path)
    assert loaded.temperature == pytest.approx(2.0)
    assert loaded.calibrate(0.5) == pytest.approx(calibrator.calibrate(0.5))


def test_fit_temperature_returns_valid_calibrator() -> None:
    calibrator = fit_temperature([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0])
    assert isinstance(calibrator, TemperatureCalibrator)
    assert 0.1 <= calibrator.temperature <= 5.0
    assert 0.0 <= calibrator.calibrate(0.75) <= 1.0


def test_isotonic_calibrator_fit_save_load(tmp_path: Path) -> None:
    calibrator = IsotonicCalibrator()
    calibrator.fit([0.1, 0.4, 0.6, 0.9], [0, 0, 1, 1])
    preds = calibrator.predict([0.2, 0.5, 0.8])
    assert preds == sorted(preds)

    path = tmp_path / "calibration" / "isotonic.pkl"
    calibrator.save(path)
    loaded = IsotonicCalibrator.load(path)
    assert loaded.predict([0.2, 0.5, 0.8]) == pytest.approx(preds)


def test_probability_calibrator_composes_steps(tmp_path: Path) -> None:
    temp_path = tmp_path / "temperature.json"
    TemperatureCalibrator(temperature=1.5).save(temp_path)

    iso_path = tmp_path / "isotonic.pkl"
    iso = IsotonicCalibrator()
    iso.fit([0.2, 0.4, 0.7, 0.9], [0, 0, 1, 1])
    iso.save(iso_path)

    calibrator = ProbabilityCalibrator.from_paths(temp_path, iso_path)
    assert calibrator is not None
    calibrated = calibrator.calibrate(0.6)
    assert 0.0 <= calibrated <= 1.0

    assert ProbabilityCalibrator.from_paths(None, None) is None


def test_uncertainty_metrics_outputs_expected_values() -> None:
    predictions = [
        {"confidence": 0.9, "correct": True},
        {"confidence": 0.1, "correct": False},
    ]
    assert expected_calibration_error(predictions, bins=10) == pytest.approx(0.1)
    assert brier_score(predictions) == pytest.approx(0.01)
    bins = calibration_bins(predictions, bins=5)
    assert len(bins) == 5
    assert sum(bin.count for bin in bins) == 2


def test_risk_model_scores_weighted_uncertainty() -> None:
    model = RiskModel(policy_weight=0.5, value_weight=0.3, dissent_weight=0.2)
    score = model.score(policy_entropy=0.4, value_variance=0.2, dissent_level=0.6)
    assert 0.0 <= score <= 1.0
    assert score == pytest.approx((0.5 * 0.4 + 0.3 * 0.2 + 0.2 * 0.6) / 1.0, rel=1e-3)


def test_reliability_plot_generates_file_when_matplotlib_available(tmp_path: Path) -> None:
    try:
        import matplotlib.pyplot as _  # noqa: F401
    except Exception:
        pytest.skip("matplotlib not available")

    plot_reliability_curve([0.2, 0.5, 0.9], [0.1, 0.6, 0.95], tmp_path)
    assert (tmp_path / "reliability_curve.png").exists()
