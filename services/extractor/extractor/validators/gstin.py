"""GSTIN format, state code and check-character validation."""

from __future__ import annotations

import re

from extractor.data.states import is_valid_gstin_state_code
from extractor.normalize import normalize_gstin
from extractor.validators.issue import Issue, error

CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# 2-digit state, 10-char PAN (5 letters, 4 digits, 1 letter), entity number, 'Z', check char.
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def check_character(first14: str) -> str:
    """Check character for the first 14 GSTIN characters.

    Each character maps to its index in 0-9A-Z. Odd positions (1-based) are multiplied by 1,
    even positions by 2. Each product contributes (product // 36) + (product % 36). With
    r = total % 36, the check character is CHARSET[(36 - r) % 36].
    """
    if len(first14) != 14:
        raise ValueError("expected exactly 14 characters")
    total = 0
    for position, char in enumerate(first14.upper(), start=1):
        value = CHARSET.index(char)
        product = value * (1 if position % 2 == 1 else 2)
        total += product // 36 + product % 36
    return CHARSET[(36 - total % 36) % 36]


def gstin_problems(raw: str | None) -> list[tuple[str, str]]:
    """(code, message) pairs describing what is wrong with a GSTIN; empty when valid."""
    gstin = normalize_gstin(raw)
    if len(gstin) != 15:
        return [("gstin_length", f"GSTIN must be 15 characters, got {len(gstin)}")]
    if not GSTIN_PATTERN.match(gstin):
        return [("gstin_format", "GSTIN does not match the 2+10+1+Z+1 format")]
    problems: list[tuple[str, str]] = []
    if not is_valid_gstin_state_code(gstin[:2]):
        problems.append(("gstin_state_code", f"'{gstin[:2]}' is not a valid GST state code"))
    expected = check_character(gstin[:14])
    if gstin[14] != expected:
        problems.append(("gstin_checksum", "GSTIN check character does not match"))
    return problems


def is_valid_gstin(raw: str | None) -> bool:
    return not gstin_problems(raw)


def validate_gstin_field(path: str, raw: str | None, required: bool) -> list[Issue]:
    if not raw:
        return [error(path, "missing", "GSTIN is missing")] if required else []
    return [error(path, code, message) for code, message in gstin_problems(raw)]
