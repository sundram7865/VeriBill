"""Field and document confidence from observable signals, never from the model's self-report.

field confidence = grounding score
                 x OCR factor        (0.5 + 0.5 x mean OCR word confidence; 1.0 for digital text)
                 x validator factor  (1.0 clean, 0.7 warning, 0.3 error)
                 x repair factor     (1.0 untouched, 0.9 repair confirmed it, 0.75 changed it)
document confidence = min(lowest required-field confidence, mean of all field confidences)
"""

from __future__ import annotations

from statistics import mean

from extractor.grounding.ground import Grounding
from extractor.schemas.invoice import REQUIRED_PATHS
from extractor.validators.issue import Issue

VALIDATOR_FACTOR = {"error": 0.3, "warn": 0.7}
REPAIR_FACTOR = {"confirmed": 0.9, "changed": 0.75}


def field_confidence(
    grounding: Grounding | None,
    issues: list[Issue],
    repair_outcome: str | None,
) -> float:
    if grounding is None or not grounding.found:
        base = 0.0
    else:
        base = grounding.score
        if grounding.ocr_conf is not None and grounding.ocr_conf < 1.0:
            base *= 0.5 + 0.5 * grounding.ocr_conf
    severities = {i.severity for i in issues}
    if "error" in severities:
        base *= VALIDATOR_FACTOR["error"]
    elif "warn" in severities:
        base *= VALIDATOR_FACTOR["warn"]
    if repair_outcome:
        base *= REPAIR_FACTOR[repair_outcome]
    return round(base, 4)


def field_confidences(
    values: dict[str, object],
    grounding: dict[str, Grounding],
    issues: list[Issue],
    repair_outcomes: dict[str, str],
) -> dict[str, float]:
    by_path: dict[str, list[Issue]] = {}
    for issue in issues:
        by_path.setdefault(issue.path, []).append(issue)
    return {
        path: field_confidence(
            grounding.get(path), by_path.get(path, []), repair_outcomes.get(path)
        )
        for path, value in values.items()
        if value is not None and value != ""
    }


def document_confidence(confidences: dict[str, float]) -> float:
    if not confidences:
        return 0.0
    required = [confidences.get(path, 0.0) for path in REQUIRED_PATHS]
    return round(min(min(required), mean(confidences.values())), 4)
