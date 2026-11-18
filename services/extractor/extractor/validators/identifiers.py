"""Invoice number and HSN/SAC code plausibility."""

from __future__ import annotations

import re

from extractor.normalize import normalize_code
from extractor.schemas.invoice import Invoice
from extractor.validators.issue import Issue, error, warn

# CGST Rule 46: up to 16 characters; letters, digits, hyphen/dash and slash.
INVOICE_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9/\-]{1,16}$")


def validate_invoice_number(raw: str | None) -> list[Issue]:
    path = "header.invoice_number"
    if not raw or not raw.strip():
        return [error(path, "missing", "Invoice number is missing")]
    if not INVOICE_NUMBER_PATTERN.match(raw.strip()):
        return [
            error(
                path,
                "invoice_number_format",
                "Invoice number must be 1-16 characters of letters, digits, '-' or '/'",
            )
        ]
    return []


def hsn_sac_problem(raw: str) -> str | None:
    code = normalize_code(raw)
    if not code.isdigit():
        return "HSN/SAC must contain digits only"
    if code.startswith("99"):
        return None if len(code) == 6 else "SAC codes (starting 99) have 6 digits"
    if len(code) not in (4, 6, 8):
        return "HSN codes have 4, 6 or 8 digits"
    return None


def validate_hsn_codes(invoice: Invoice) -> list[Issue]:
    issues: list[Issue] = []
    for index, item in enumerate(invoice.line_items):
        path = f"line_items.{index}.hsn_sac"
        if not item.hsn_sac:
            issues.append(warn(path, "missing", "HSN/SAC code is missing"))
            continue
        problem = hsn_sac_problem(item.hsn_sac)
        if problem:
            issues.append(error(path, "hsn_sac_format", problem))
    return issues
