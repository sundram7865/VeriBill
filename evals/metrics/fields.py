"""Field-level comparison of a prediction against ground truth.

Each field ends up as one of:
  tp  both present and equal (after normalisation)
  fp  predicted a value that is absent from ground truth
  fn  ground truth has a value the prediction missed
  wrong  both present but different: counted as one fp AND one fn (standard for extraction)
  tn  both absent: not counted
Line items are aligned by position, because the model is asked to return them in document order.
"""

from __future__ import annotations

from dataclasses import dataclass

from extractor.normalize import ZERO_WHEN_ABSENT, canonical, values_equal
from extractor.schemas.paths import field_name, flatten, generic_path


@dataclass(frozen=True)
class FieldResult:
    path: str
    generic: str
    status: str  # tp | fp | fn | wrong | tn
    expected: str | float | None
    predicted: str | float | None

    @property
    def correct(self) -> bool:
        return self.status in ("tp", "tn")


def _present(path: str, value: str | float | None) -> bool:
    if value is None:
        return False
    return not (field_name(path) in ZERO_WHEN_ABSENT and value == 0.0)


def compare_field(path: str, expected_raw, predicted_raw) -> FieldResult:
    expected, predicted = canonical(path, expected_raw), canonical(path, predicted_raw)
    has_expected, has_predicted = _present(path, expected), _present(path, predicted)
    if not has_expected and not has_predicted:
        status = "tn"
    elif has_expected and not has_predicted:
        status = "fn"
    elif has_predicted and not has_expected:
        status = "fp"
    else:
        status = "tp" if values_equal(path, expected_raw, predicted_raw) else "wrong"
    return FieldResult(path, generic_path(path), status, expected, predicted)


def compare_invoice(ground_truth: dict, prediction: dict | None) -> list[FieldResult]:
    expected = flatten(ground_truth)
    predicted = flatten(prediction) if prediction else {}
    paths = list(expected) + [p for p in predicted if p not in expected]
    return [compare_field(p, expected.get(p), predicted.get(p)) for p in paths]


def is_fully_correct(results: list[FieldResult]) -> bool:
    return all(r.correct for r in results)
