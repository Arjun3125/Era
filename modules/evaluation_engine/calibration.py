"""Confidence calibration metrics for ERA evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class CalibrationBin:
    confidence_avg: float
    accuracy: float
    count: int


def expected_calibration_error(
    predictions: Iterable[dict],
    *,
    bins: int = 10,
) -> float:
    bucket_counts = [0] * bins
    bucket_conf = [0.0] * bins
    bucket_acc = [0.0] * bins

    for item in predictions:
        confidence = float(item.get("confidence", 0.0) or 0.0)
        correct = 1.0 if item.get("correct", False) else 0.0
        index = min(bins - 1, int(confidence * bins))
        bucket_counts[index] += 1
        bucket_conf[index] += confidence
        bucket_acc[index] += correct

    total = sum(bucket_counts)
    if total == 0:
        return 0.0

    ece = 0.0
    for idx in range(bins):
        count = bucket_counts[idx]
        if count == 0:
            continue
        acc = bucket_acc[idx] / count
        conf = bucket_conf[idx] / count
        ece += (count / total) * abs(acc - conf)
    return round(ece, 4)


def calibration_bins(predictions: Iterable[dict], *, bins: int = 10) -> List[CalibrationBin]:
    bucket_counts = [0] * bins
    bucket_conf = [0.0] * bins
    bucket_acc = [0.0] * bins

    for item in predictions:
        confidence = float(item.get("confidence", 0.0) or 0.0)
        correct = 1.0 if item.get("correct", False) else 0.0
        index = min(bins - 1, int(confidence * bins))
        bucket_counts[index] += 1
        bucket_conf[index] += confidence
        bucket_acc[index] += correct

    output: List[CalibrationBin] = []
    for idx in range(bins):
        count = bucket_counts[idx]
        if count == 0:
            output.append(CalibrationBin(0.0, 0.0, 0))
            continue
        output.append(
            CalibrationBin(
                confidence_avg=bucket_conf[idx] / count,
                accuracy=bucket_acc[idx] / count,
                count=count,
            )
        )
    return output
