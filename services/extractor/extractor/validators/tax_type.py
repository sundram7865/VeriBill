"""Intra-state supply must charge CGST + SGST; inter-state must charge IGST. Never both."""

from __future__ import annotations

from extractor.data.states import state_code_from_text
from extractor.normalize import normalize_gstin
from extractor.schemas.invoice import Invoice, LineItem
from extractor.validators.issue import Issue, error, warn


def _positive(value: float | None) -> bool:
    return value is not None and value > 0


def _has_split_tax(item: LineItem) -> bool:
    return _positive(item.cgst_amount) or _positive(item.sgst_amount)


def validate_tax_type(invoice: Invoice) -> list[Issue]:
    issues: list[Issue] = []
    for index, item in enumerate(invoice.line_items):
        if _has_split_tax(item) and _positive(item.igst_amount):
            issues.append(
                error(
                    f"line_items.{index}.igst_amount",
                    "tax_type_both",
                    "Line charges both IGST and CGST/SGST; an invoice uses one or the other",
                )
            )

    supplier_gstin = normalize_gstin(invoice.header.supplier_gstin)
    supplier_state = supplier_gstin[:2] if len(supplier_gstin) == 15 else None
    supply_state = state_code_from_text(invoice.header.place_of_supply)
    if supplier_state is None or supply_state is None:
        issues.append(
            warn(
                "header.place_of_supply",
                "tax_type_unknown",
                "Cannot check tax type: supplier state or place of supply is unknown",
            )
        )
        return issues

    intra_state = supplier_state == supply_state
    for index, item in enumerate(invoice.line_items):
        if intra_state and _positive(item.igst_amount):
            issues.append(
                error(
                    f"line_items.{index}.igst_amount",
                    "tax_type_mismatch",
                    f"Supplier state {supplier_state} equals place of supply, so expect "
                    "CGST + SGST, not IGST",
                )
            )
        if not intra_state and _has_split_tax(item):
            path = "cgst_amount" if _positive(item.cgst_amount) else "sgst_amount"
            issues.append(
                error(
                    f"line_items.{index}.{path}",
                    "tax_type_mismatch",
                    f"Supplier state {supplier_state} differs from place of supply "
                    f"{supply_state}, so expect IGST, not CGST/SGST",
                )
            )
    return issues
