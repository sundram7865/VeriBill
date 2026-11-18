"""Auto-approval threshold analysis: how many documents skip review, and how safe that is."""

from __future__ import annotations

from evals.metrics.aggregate import CaseResult
from evals.metrics.scores import rate

DEFAULT_THRESHOLDS = (0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.98)


def would_auto_approve(result: CaseResult, threshold: float) -> bool:
    """Mirror of the decide node's rule, re-evaluated at a different threshold."""
    p = result.prediction
    if p.decision in ("failed", "reject"):
        return False
    return (not p.has_errors) and p.required_grounded and p.document_confidence >= threshold


def threshold_table(results: list[CaseResult], thresholds=DEFAULT_THRESHOLDS) -> list[dict]:
    rows = []
    for threshold in thresholds:
        auto = [r for r in results if would_auto_approve(r, threshold)]
        rows.append(
            {
                "threshold": threshold,
                "auto_approval_rate": rate(len(auto), len(results)),
                "auto_approved_accuracy": rate(
                    sum(r.correct_to_auto_approve for r in auto), len(auto)
                ),
                "auto_approved": len(auto),
            }
        )
    return rows


def pick_threshold(rows: list[dict], target_accuracy: float) -> float | None:
    """Lowest threshold whose auto-approved accuracy meets the target (maximises automation).

    Returns None when no threshold auto-approves anything at the target accuracy.
    """
    for row in sorted(rows, key=lambda r: r["threshold"]):
        accuracy = row["auto_approved_accuracy"]
        if row["auto_approved"] > 0 and accuracy is not None and accuracy >= target_accuracy:
            return row["threshold"]
    return None
