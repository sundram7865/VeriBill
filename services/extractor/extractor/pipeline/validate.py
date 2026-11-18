"""Node 5, validate: deterministic validators plus grounding failures, as one issue list."""

from __future__ import annotations

from extractor.grounding.ground import Grounding
from extractor.schemas.invoice import REQUIRED_PATHS, Invoice
from extractor.validators.issue import Issue, error, warn
from extractor.validators.runner import ValidationConfig, validate_invoice


def grounding_issues(grounding: dict[str, Grounding]) -> list[Issue]:
    issues = []
    for path, result in grounding.items():
        if result.found:
            continue
        message = "Value not found in the document text"
        issues.append(
            error(path, "not_grounded", message)
            if path in REQUIRED_PATHS
            else warn(path, "not_grounded", message)
        )
    return issues


def collect_issues(
    invoice: Invoice,
    grounding: dict[str, Grounding],
    normalization_issues: list[Issue],
    config: ValidationConfig,
) -> list[Issue]:
    issues = [
        *normalization_issues,
        *validate_invoice(invoice, config),
        *grounding_issues(grounding),
    ]
    # One message per (path, code) keeps the review screen readable.
    unique: dict[tuple[str, str], Issue] = {}
    for issue in issues:
        unique.setdefault((issue.path, issue.code), issue)
    return list(unique.values())


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)
