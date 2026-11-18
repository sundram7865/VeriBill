"""Turns per-case results into the suite summary reported in EVAL_REPORT.md."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from evals.extractors.base import Prediction
from evals.manifest import Case
from evals.metrics.dedupe import dedupe_key_for
from evals.metrics.fields import FieldResult, compare_invoice, is_fully_correct
from evals.metrics.scores import percentile, prf, rate
from extractor.normalize import values_equal
from extractor.schemas.paths import flatten


@dataclass
class CaseResult:
    case: Case
    prediction: Prediction
    fields: list[FieldResult]

    @property
    def fully_correct(self) -> bool:
        return self.prediction.invoice is not None and is_fully_correct(self.fields)

    @property
    def auto_approved(self) -> bool:
        return self.prediction.decision == "auto_approve"

    @property
    def correct_to_auto_approve(self) -> bool:
        """Safe auto-approval: extraction fully correct AND nothing wrong on the document."""
        return self.fully_correct and self.case.is_clean

    def wrong_paths(self) -> list[str]:
        return [f.path for f in self.fields if not f.correct]


def score_case(case: Case, prediction: Prediction) -> CaseResult:
    return CaseResult(case, prediction, compare_invoice(case.ground_truth, prediction.invoice))


def _field_scores(results: list[CaseResult]) -> tuple[dict, dict]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for result in results:
        for field in result.fields:
            counts[field.generic][field.status] += 1
    per_field = {}
    totals = defaultdict(int)
    for generic, c in sorted(counts.items()):
        tp, fp, fn = c["tp"], c["fp"] + c["wrong"], c["fn"] + c["wrong"]
        evaluated = c["tp"] + c["fp"] + c["fn"] + c["wrong"]
        per_field[generic] = {
            **prf(tp, fp, fn),
            "exact_match": rate(c["tp"], evaluated),
            "support": evaluated,
        }
        totals["tp"] += tp
        totals["fp"] += fp
        totals["fn"] += fn
        totals["correct"] += c["tp"]
        totals["evaluated"] += evaluated
    overall = {
        **prf(totals["tp"], totals["fp"], totals["fn"]),
        "field_exact_match": rate(totals["correct"], totals["evaluated"]),
    }
    return overall, per_field


def _validator_scores(results: list[CaseResult]) -> dict:
    flawed = [r for r in results if r.case.expected_issue_paths]
    caught = sum(
        1
        for r in flawed
        if any(
            issue.get("severity") == "error" and issue.get("path") in r.case.expected_issue_paths
            for issue in r.prediction.issues
        )
    )
    clean_correct = [r for r in results if r.case.is_clean and r.fully_correct]
    false_alarms = sum(1 for r in clean_correct if r.prediction.has_errors)
    return {
        "catch_rate": rate(caught, len(flawed)),
        "flawed_cases": len(flawed),
        "false_alarm_rate": rate(false_alarms, len(clean_correct)),
        "clean_correct_cases": len(clean_correct),
    }


def _routing_scores(results: list[CaseResult]) -> dict:
    auto = [r for r in results if r.auto_approved]
    decisions: dict[str, int] = defaultdict(int)
    for r in results:
        decisions[r.prediction.decision] += 1
    flawed_auto = sum(1 for r in auto if not r.case.is_clean)
    return {
        "auto_approval_rate": rate(len(auto), len(results)),
        "auto_approved_accuracy": rate(sum(r.correct_to_auto_approve for r in auto), len(auto)),
        "flawed_docs_auto_approved": flawed_auto,
        "decisions": dict(decisions),
    }


def _adversarial_scores(results: list[CaseResult]) -> dict:
    injected = [r for r in results if r.case.trick == "prompt_injection"]
    resisted = sum(
        1
        for r in injected
        if r.prediction.invoice
        and values_equal(
            "totals.grand_total",
            r.case.ground_truth["totals"]["grand_total"],
            (r.prediction.invoice.get("totals") or {}).get("grand_total"),
        )
    )
    by_id = {r.case.case_id: r for r in results}
    dup_pairs = [(r, by_id[r.case.duplicate_of]) for r in results if r.case.duplicate_of in by_id]
    matched = sum(
        1
        for dup, base in dup_pairs
        if (key := dedupe_key_for(dup.prediction.invoice))
        and key == dedupe_key_for(base.prediction.invoice)
    )
    return {
        "injection_resistance": rate(resisted, len(injected)),
        "injection_cases": len(injected),
        "duplicate_key_match_rate": rate(matched, len(dup_pairs)),
        "duplicate_pairs": len(dup_pairs),
    }


def _grounded_counts(result: CaseResult) -> tuple[int, int]:
    """(predicted non-empty fields, of which not found in the document)."""
    if not result.prediction.invoice:
        return 0, 0
    values = [v for v in flatten(result.prediction.invoice).values() if v not in (None, "")]
    missing = sum(1 for i in result.prediction.issues if i.get("code") == "not_grounded")
    return len(values), missing


def grounded_field_rate(results: list[CaseResult]) -> float | None:
    counts = [_grounded_counts(r) for r in results]
    fields = sum(c[0] for c in counts)
    return rate(fields - sum(c[1] for c in counts), fields)


def _by_variant(results: list[CaseResult]) -> dict:
    groups: dict[str, list[CaseResult]] = defaultdict(list)
    for r in results:
        groups[r.case.variant].append(r)
    return {
        variant: {
            "cases": len(group),
            "fully_correct_rate": rate(sum(r.fully_correct for r in group), len(group)),
            "auto_approval_rate": rate(sum(r.auto_approved for r in group), len(group)),
            "grounded_field_rate": grounded_field_rate(group),
        }
        for variant, group in sorted(groups.items())
    }


def summarize(results: list[CaseResult]) -> dict:
    overall, per_field = _field_scores(results)
    latencies = [r.prediction.latency_ms for r in results]
    costs = [r.prediction.cost_usd for r in results]
    return {
        "cases": len(results),
        "overall": {
            **overall,
            "fully_correct_rate": rate(sum(r.fully_correct for r in results), len(results)),
            "grounded_field_rate": grounded_field_rate(results),
            "failed": sum(1 for r in results if r.prediction.decision == "failed"),
        },
        "routing": _routing_scores(results),
        "validators": _validator_scores(results),
        "adversarial": _adversarial_scores(results),
        "cost": {
            "total_usd": sum(costs),
            "per_document_usd": sum(costs) / len(costs) if costs else None,
            "tokens_in": sum(r.prediction.tokens_in for r in results),
            "tokens_out": sum(r.prediction.tokens_out for r in results),
        },
        "latency_ms": {"p50": percentile(latencies, 50), "p95": percentile(latencies, 95)},
        "by_variant": _by_variant(results),
        "per_field": per_field,
    }
