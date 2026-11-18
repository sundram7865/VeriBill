"""Precision / recall / F1 and percentiles."""

from __future__ import annotations

import math
from collections.abc import Iterable


def prf(tp: int, fp: int, fn: int) -> dict[str, float | None]:
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if tp == 0:
        # Nothing right: F1 is 0 whenever there was anything to get right or wrong.
        return {"precision": precision, "recall": recall, "f1": 0.0 if fp + fn else None}
    f1 = 2 * precision * recall / (precision + recall)  # type: ignore[operator]
    return {"precision": precision, "recall": recall, "f1": f1}


def rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def percentile(values: Iterable[float], pct: float) -> float | None:
    """Nearest-rank percentile (pct in 0..100): simple and easy to explain."""
    ordered = sorted(values)
    if not ordered:
        return None
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]
