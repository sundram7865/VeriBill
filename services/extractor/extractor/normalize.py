"""Deterministic normalisation of printed values. Shared by grounding, validators and evals.

Indian invoices print the same value many ways ("Rs. 1,23,456.00", "123456.00/-", "15-Mar-2025",
"15/03/2025"). Comparing normalised forms is what makes "exact match" fair.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from extractor.data.states import state_code_from_text
from extractor.schemas.field_types import FieldType, field_type

AMOUNT_TOLERANCE_EXACT = 0.005  # values are compared at paise precision

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d-%b-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d-%B-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d/%m/%y",
    "%d-%m-%y",
)
_CURRENCY_TOKENS = re.compile(r"(rs\.?|inr|₹|/-)", re.IGNORECASE)


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    text = value.casefold().replace("&", " and ")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_code(value: str | None) -> str:
    return re.sub(r"\s+", "", value or "").upper()


def normalize_gstin(value: str | None) -> str:
    return re.sub(r"[\s\-]", "", value or "").upper()


def parse_amount(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = _CURRENCY_TOKENS.sub("", value).strip()
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace(",", "").replace(" ", "")
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", text):
        return None
    number = float(text)
    return -number if negative else number


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = re.sub(r"\s+", " ", value.strip()).rstrip(".")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


# For these fields "not printed" and "0" mean the same thing (no discount, no IGST on an
# intra-state invoice, no round-off), so both canonicalise to 0.0.
ZERO_WHEN_ABSENT = frozenset(
    {
        "discount",
        "round_off",
        "cgst_rate",
        "cgst_amount",
        "sgst_rate",
        "sgst_amount",
        "igst_rate",
        "igst_amount",
    }
)


def canonical(path: str, value: str | float | int | None) -> str | float | None:
    """Canonical form of a field value, used for equality and for display-independent keys."""
    if (value is None or value == "") and path.rsplit(".", 1)[-1] in ZERO_WHEN_ABSENT:
        return 0.0
    if value is None or value == "":
        return None
    kind = field_type(path)
    if kind in (FieldType.AMOUNT, FieldType.NUMBER):
        number = parse_amount(value)
        return None if number is None else round(number, 2)
    if kind == FieldType.DATE:
        parsed = parse_date(str(value))
        return parsed.isoformat() if parsed else normalize_text(str(value))
    if kind == FieldType.GSTIN:
        return normalize_gstin(str(value))
    if kind == FieldType.CODE:
        return normalize_code(str(value))
    if kind == FieldType.STATE:
        return state_code_from_text(str(value)) or normalize_text(str(value))
    if kind == FieldType.CURRENCY:
        return normalize_code(str(value))
    return normalize_text(str(value))


def values_equal(path: str, a: str | float | int | None, b: str | float | int | None) -> bool:
    ca, cb = canonical(path, a), canonical(path, b)
    if isinstance(ca, float) and isinstance(cb, float):
        return abs(ca - cb) < AMOUNT_TOLERANCE_EXACT
    return ca == cb
