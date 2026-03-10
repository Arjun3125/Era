"""Calibration utilities for value model outputs."""

from __future__ import annotations

from typing import Iterable, Tuple

from sklearn.isotonic import IsotonicRegression


def fit_isotonic(preds: Iterable[float], targets: Iterable[float]) -> IsotonicRegression:
    model = IsotonicRegression(out_of_bounds="clip")
    model.fit(list(preds), list(targets))
    return model


def apply_isotonic(model: IsotonicRegression, preds: Iterable[float]) -> Tuple[float, ...]:
    return tuple(float(value) for value in model.predict(list(preds)))
