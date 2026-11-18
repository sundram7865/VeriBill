"""Shared builders for extractor tests."""

from __future__ import annotations

import copy

from extractor.schemas.invoice import Invoice

VALID_GSTIN_MH = "27AAPFU0939F1ZV"  # official test vector, Maharashtra
VALID_GSTIN_KA = "29AAACK1234L1ZJ"  # check character computed by check_character()


def invoice_dict(intra: bool = True) -> dict:
    line = {
        "description": "Copper Wire 2.5 sq mm",
        "hsn_sac": "8544",
        "quantity": 10.0,
        "unit": "MTR",
        "rate": 100.0,
        "discount": 0.0,
        "taxable_value": 1000.0,
        "cgst_rate": 9.0 if intra else None,
        "cgst_amount": 90.0 if intra else None,
        "sgst_rate": 9.0 if intra else None,
        "sgst_amount": 90.0 if intra else None,
        "igst_rate": None if intra else 18.0,
        "igst_amount": None if intra else 180.0,
    }
    return {
        "header": {
            "supplier_name": "Kaveri Steel Pvt Ltd",
            "supplier_gstin": VALID_GSTIN_MH,
            "buyer_name": "Deccan Foods LLP",
            "buyer_gstin": VALID_GSTIN_KA,
            "invoice_number": "INV/2025-26/0042",
            "invoice_date": "2026-03-15",
            "place_of_supply": "Maharashtra (27)" if intra else "Karnataka (29)",
            "currency": "INR",
        },
        "line_items": [line],
        "totals": {"subtotal": 1000.0, "total_tax": 180.0, "round_off": 0.0, "grand_total": 1180.0},
    }


def make_invoice(intra: bool = True, **changes) -> Invoice:
    data = copy.deepcopy(invoice_dict(intra))
    for path, value in changes.items():
        section, _, name = path.partition("__")
        if section == "line":
            data["line_items"][0][name] = value
        else:
            data[section][name] = value
    return Invoice.model_validate(data)


def _as_text(value) -> str | None:
    if value is None:
        return None
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def raw_dict(intra: bool = True, **changes) -> dict:
    """The model's as-printed reading of invoice_dict(); `changes` override raw strings."""
    data = invoice_dict(intra)
    raw = {
        "header": {k: _as_text(v) for k, v in data["header"].items()},
        "line_items": [{k: _as_text(v) for k, v in item.items()} for item in data["line_items"]],
        "totals": {k: _as_text(v) for k, v in data["totals"].items()},
    }
    raw["header"]["invoice_date"] = "15/03/2026"  # printed format, normalised by our code
    for path, value in changes.items():
        section, _, name = path.partition("__")
        if section == "line":
            raw["line_items"][0][name] = value
        else:
            raw[section][name] = value
    return raw
