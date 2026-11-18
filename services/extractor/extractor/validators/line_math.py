"""Per-line arithmetic: quantity x rate - discount = taxable value; tax = taxable x rate%."""

from __future__ import annotations

from extractor.schemas.invoice import Invoice, LineItem
from extractor.validators.issue import Issue, error, warn

TAX_PAIRS = (
    ("cgst_rate", "cgst_amount"),
    ("sgst_rate", "sgst_amount"),
    ("igst_rate", "igst_amount"),
)


def _check_taxable(index: int, item: LineItem, tolerance: float) -> list[Issue]:
    if item.quantity is None or item.rate is None or item.taxable_value is None:
        return []
    expected = item.quantity * item.rate - (item.discount or 0.0)
    if abs(expected - item.taxable_value) <= tolerance:
        return []
    return [
        error(
            f"line_items.{index}.taxable_value",
            "line_taxable_mismatch",
            f"quantity x rate - discount = {expected:.2f} but taxable value is "
            f"{item.taxable_value:.2f}",
        )
    ]


def _check_tax_amounts(index: int, item: LineItem, tolerance: float) -> list[Issue]:
    issues: list[Issue] = []
    if item.taxable_value is None:
        return issues
    for rate_field, amount_field in TAX_PAIRS:
        rate, amount = getattr(item, rate_field), getattr(item, amount_field)
        if rate is None or amount is None:
            continue
        expected = item.taxable_value * rate / 100
        if abs(expected - amount) > tolerance:
            issues.append(
                error(
                    f"line_items.{index}.{amount_field}",
                    "line_tax_mismatch",
                    f"taxable value x {rate:g}% = {expected:.2f} "
                    f"but {amount_field} is {amount:.2f}",
                )
            )
    if (
        item.cgst_rate is not None
        and item.sgst_rate is not None
        and item.cgst_rate != item.sgst_rate
    ):
        issues.append(
            warn(
                f"line_items.{index}.sgst_rate",
                "cgst_sgst_rate_differs",
                "CGST and SGST rates are normally equal",
            )
        )
    return issues


def validate_line_math(invoice: Invoice, tolerance: float) -> list[Issue]:
    issues: list[Issue] = []
    for index, item in enumerate(invoice.line_items):
        issues += _check_taxable(index, item, tolerance)
        issues += _check_tax_amounts(index, item, tolerance)
    return issues
