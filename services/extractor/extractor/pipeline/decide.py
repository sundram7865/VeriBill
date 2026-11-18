"""Node 7, decide: auto-approve only when nothing is wrong and confidence clears the bar."""

from __future__ import annotations

from dataclasses import dataclass

from extractor.grounding.ground import Grounding
from extractor.schemas.invoice import REQUIRED_PATHS
from extractor.validators.issue import Issue


@dataclass(frozen=True)
class Decision:
    route: str  # auto_approve | needs_review | reject
    reason: str
    required_grounded: bool


def required_fields_grounded(grounding: dict[str, Grounding]) -> bool:
    return all(grounding.get(path) is not None and grounding[path].found for path in REQUIRED_PATHS)


def decide(
    issues: list[Issue],
    grounding: dict[str, Grounding],
    doc_confidence: float,
    threshold: float,
    unreadable: bool,
) -> Decision:
    grounded = required_fields_grounded(grounding)
    if unreadable:
        return Decision("reject", "No readable text was found in the document", grounded)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        return Decision("needs_review", f"{len(errors)} validation error(s)", grounded)
    if not grounded:
        return Decision(
            "needs_review", "A required field could not be found in the document", grounded
        )
    if doc_confidence < threshold:
        return Decision(
            "needs_review",
            f"Confidence {doc_confidence:.2f} is below the {threshold:.2f} threshold",
            grounded,
        )
    return Decision("auto_approve", "All checks passed", grounded)
