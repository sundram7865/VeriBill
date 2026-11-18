"""Type-aware scoring of a candidate span against an extracted value (0 = no match, 1 = exact)."""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from extractor.data.states import state_code_from_text
from extractor.normalize import (
    normalize_code,
    normalize_gstin,
    normalize_text,
    parse_amount,
    parse_date,
)
from extractor.schemas.field_types import FieldType

# Labels glued to a value by OCR or layout, e.g. "No:INV-1" or "GSTIN:29ABC...".
_LABEL_PREFIX = re.compile(r"^[A-Za-z .#]*[:]\s*")
_CURRENCY_WORDS = {"INR", "RS", "RS.", "₹", "RUPEES"}


# Characters OCR glues onto values from table borders and label punctuation.
_BORDER_CHARS = "|[]{}:;'\"`_."


def _strip_borders(text: str) -> str:
    return text.strip().strip(_BORDER_CHARS).strip()


def _number_from_text(text: str) -> float | None:
    cleaned = _strip_borders(_LABEL_PREFIX.sub("", text.strip())).rstrip("%").strip()
    return parse_amount(cleaned)


def score_number(value: float, text: str) -> float:
    number = _number_from_text(text)
    return 1.0 if number is not None and abs(number - value) < 0.005 else 0.0


def score_date(value: str, text: str) -> float:
    parsed = parse_date(_strip_borders(_LABEL_PREFIX.sub("", text)))
    return 1.0 if parsed is not None and parsed.isoformat() == value else 0.0


def score_state(value: str, text: str) -> float:
    expected = state_code_from_text(value)
    return 1.0 if expected is not None and state_code_from_text(text) == expected else 0.0


def score_code(value: str, text: str, normalizer=normalize_code) -> float:
    expected = normalizer(value)
    candidate = normalizer(_strip_borders(_LABEL_PREFIX.sub("", text)))
    if not expected or not candidate:
        return 0.0
    if candidate == expected:
        return 1.0
    # OCR confusions (0/O, 1/I, 5/S) cost a little confidence instead of failing outright.
    if len(candidate) == len(expected):
        return fuzz.ratio(candidate, expected) / 100
    return 0.0


def score_text(value: str, text: str) -> float:
    expected, candidate = normalize_text(value), normalize_text(text)
    if not expected or not candidate:
        return 0.0
    return fuzz.ratio(expected, candidate) / 100


def score_currency(value: str, text: str) -> float:
    token = _strip_borders(text).upper()
    if token == value.upper():
        return 1.0
    return 1.0 if value.upper() == "INR" and token in _CURRENCY_WORDS else 0.0


def score(kind: FieldType, value: object, text: str) -> float:
    if kind in (FieldType.AMOUNT, FieldType.NUMBER):
        return score_number(float(value), text)  # type: ignore[arg-type]
    if kind == FieldType.DATE:
        return score_date(str(value), text)
    if kind == FieldType.STATE:
        return score_state(str(value), text)
    if kind == FieldType.GSTIN:
        return score_code(str(value), text, normalize_gstin)
    if kind == FieldType.CODE:
        return score_code(str(value), text)
    if kind == FieldType.CURRENCY:
        return score_currency(str(value), text)
    return score_text(str(value), text)


def max_window_words(kind: FieldType, value: object) -> int:
    """How many words a printed value can span, to keep the candidate search small."""
    if kind in (FieldType.AMOUNT, FieldType.NUMBER, FieldType.GSTIN, FieldType.CURRENCY):
        return 2
    if kind in (FieldType.DATE, FieldType.CODE):
        return 3
    if kind == FieldType.STATE:
        return 4
    return len(str(value).split()) + 2
