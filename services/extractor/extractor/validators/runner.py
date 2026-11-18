"""Runs every validator over an invoice and returns the combined list of issues."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from extractor.schemas.invoice import Invoice
from extractor.validators.dates import validate_invoice_date
from extractor.validators.gstin import validate_gstin_field
from extractor.validators.identifiers import validate_hsn_codes, validate_invoice_number
from extractor.validators.issue import Issue, error
from extractor.validators.line_math import validate_line_math
from extractor.validators.tax_type import validate_tax_type
from extractor.validators.totals import validate_totals


@dataclass(frozen=True)
class ValidationConfig:
    today: date
    max_invoice_age_days: int = 3 * 365
    amount_tolerance: float = 1.0


def _required_presence(invoice: Invoice) -> list[Issue]:
    issues: list[Issue] = []
    if not invoice.header.supplier_name:
        issues.append(error("header.supplier_name", "missing", "Supplier name is missing"))
    if invoice.totals.grand_total is None:
        issues.append(error("totals.grand_total", "missing", "Grand total is missing"))
    if not invoice.line_items:
        issues.append(error("line_items.0.description", "no_line_items", "No line items found"))
    return issues


def validate_invoice(invoice: Invoice, config: ValidationConfig) -> list[Issue]:
    header = invoice.header
    tolerance = config.amount_tolerance
    return [
        *_required_presence(invoice),
        *validate_gstin_field("header.supplier_gstin", header.supplier_gstin, required=True),
        *validate_gstin_field("header.buyer_gstin", header.buyer_gstin, required=False),
        *validate_invoice_number(header.invoice_number),
        *validate_invoice_date(header.invoice_date, config.today, config.max_invoice_age_days),
        *validate_hsn_codes(invoice),
        *validate_tax_type(invoice),
        *validate_line_math(invoice, tolerance),
        *validate_totals(invoice, tolerance),
    ]
