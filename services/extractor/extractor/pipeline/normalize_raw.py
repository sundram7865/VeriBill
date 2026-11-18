"""Deterministic conversion of the model's as-printed strings into a typed Invoice.

Values that cannot be parsed become None plus a "format" issue, so they go to review instead of
being silently dropped or guessed.
"""

from __future__ import annotations

from extractor.normalize import normalize_code, parse_amount, parse_date
from extractor.schemas.field_types import FieldType, field_type
from extractor.schemas.invoice import Invoice
from extractor.schemas.paths import flatten
from extractor.validators.issue import Issue, error

_PERCENT_SUFFIX = "%"


def _parse_number(raw: str) -> float | None:
    return parse_amount(raw.strip().rstrip(_PERCENT_SUFFIX).strip())


def _normalize_value(path: str, raw: str | None) -> tuple[object, Issue | None]:
    if raw is None or not str(raw).strip():
        return None, None
    text = str(raw).strip()
    kind = field_type(path)
    if kind in (FieldType.AMOUNT, FieldType.NUMBER):
        number = _parse_number(text)
        if number is None:
            return None, error(path, "number_format", f"Could not read '{text}' as a number")
        return round(number, 4), None
    if kind == FieldType.DATE:
        parsed = parse_date(text)
        if parsed is None:
            return None, error(path, "date_format", f"Could not read '{text}' as a date")
        return parsed.isoformat(), None
    if kind == FieldType.GSTIN:
        return normalize_code(text).replace("-", ""), None
    if kind == FieldType.CURRENCY:
        return _currency(text), None
    return text, None


def _currency(text: str) -> str:
    upper = text.upper().replace(".", "")
    return "INR" if upper in ("RS", "INR", "₹", "RUPEES") else upper


def normalize_raw(raw: dict) -> tuple[Invoice, list[Issue]]:
    issues: list[Issue] = []
    typed: dict = {"header": {}, "line_items": [], "totals": {}}
    for path, value in flatten(raw).items():
        normalized, issue = _normalize_value(path, value)  # type: ignore[arg-type]
        if issue:
            issues.append(issue)
        parts = path.split(".")
        if parts[0] == "line_items":
            index = int(parts[1])
            while len(typed["line_items"]) <= index:
                typed["line_items"].append({})
            typed["line_items"][index][parts[2]] = normalized
        else:
            typed[parts[0]][parts[1]] = normalized
    return Invoice.model_validate(typed), issues
