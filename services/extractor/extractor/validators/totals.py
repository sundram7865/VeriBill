"""Document totals: lines sum to subtotal and tax; subtotal + tax + round-off = grand total."""

from __future__ import annotations

from extractor.schemas.invoice import Invoice
from extractor.validators.issue import Issue, error, warn

_TAX_AMOUNT_FIELDS = ("cgst_amount", "sgst_amount", "igst_amount")


def _sum_or_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) if present else None


def validate_totals(invoice: Invoice, tolerance: float) -> list[Issue]:
    totals = invoice.totals
    issues: list[Issue] = []

    line_subtotal = _sum_or_none([item.taxable_value for item in invoice.line_items])
    subtotal = totals.subtotal
    if (
        line_subtotal is not None
        and subtotal is not None
        and abs(line_subtotal - subtotal) > tolerance
    ):
        issues.append(
            error(
                "totals.subtotal",
                "subtotal_mismatch",
                f"Line taxable values sum to {line_subtotal:.2f} but subtotal is "
                f"{totals.subtotal:.2f}",
            )
        )

    line_tax = _sum_or_none(
        [getattr(item, f) for item in invoice.line_items for f in _TAX_AMOUNT_FIELDS]
    )
    total_tax = totals.total_tax
    if line_tax is not None and total_tax is not None and abs(line_tax - total_tax) > tolerance:
        issues.append(
            error(
                "totals.total_tax",
                "total_tax_mismatch",
                f"Line taxes sum to {line_tax:.2f} but total tax is {totals.total_tax:.2f}",
            )
        )

    round_off = totals.round_off or 0.0
    if abs(round_off) >= 1.0:
        issues.append(
            warn("totals.round_off", "round_off_large", "Round-off should be less than Rs 1")
        )

    if None not in (totals.subtotal, totals.total_tax, totals.grand_total):
        expected = totals.subtotal + totals.total_tax + round_off  # type: ignore[operator]
        if abs(expected - totals.grand_total) > tolerance:  # type: ignore[operator]
            issues.append(
                error(
                    "totals.grand_total",
                    "grand_total_mismatch",
                    f"subtotal + total tax + round-off = {expected:.2f} but grand total is "
                    f"{totals.grand_total:.2f}",
                )
            )
    return issues
