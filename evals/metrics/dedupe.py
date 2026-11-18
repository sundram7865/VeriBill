"""Duplicate key, mirrored from the API (apps/api/src/modules/documents/dedupeKey.ts).

Both implementations are checked against evals/fixtures/dedupe_vectors.json.
"""

from __future__ import annotations

import hashlib
import re


def normalize_invoice_number(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def dedupe_key(
    supplier_gstin: str | None, invoice_number: str | None, grand_total: float | None
) -> str | None:
    if not supplier_gstin or not invoice_number or grand_total is None:
        return None
    gstin = re.sub(r"[\s\-]", "", supplier_gstin).upper()
    material = f"{gstin}|{normalize_invoice_number(invoice_number)}|{grand_total:.2f}"
    return hashlib.sha256(material.encode()).hexdigest()


def dedupe_key_for(invoice: dict | None) -> str | None:
    if not invoice:
        return None
    header, totals = invoice.get("header") or {}, invoice.get("totals") or {}
    return dedupe_key(
        header.get("supplier_gstin"), header.get("invoice_number"), totals.get("grand_total")
    )
