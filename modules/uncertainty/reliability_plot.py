"""Reliability diagram plotting."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    return plt


def plot_reliability_curve(
    confidences: Iterable[float],
    accuracies: Iterable[float],
    output_dir: Path,
    *,
    filename: str = "reliability_curve.png",
) -> None:
    plt = _require_matplotlib()
    if plt is None:
        return
    conf = list(confidences)
    acc = list(accuracies)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(conf, acc, marker="o")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
    ax.set_title("Reliability")
    ax.set_xlabel("Confidence")
    ax.set_ylabel("Accuracy")
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / filename)
    plt.close(fig)
