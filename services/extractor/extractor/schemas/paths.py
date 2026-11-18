"""Flatten an invoice into dotted field paths and back.

Paths look like "header.supplier_gstin", "line_items.2.rate" and "totals.grand_total". Every
other component (grounding, validators, confidence, metrics, the UI) speaks in these paths.
"""

from __future__ import annotations

from typing import Any

from extractor.schemas.invoice import HEADER_FIELDS, LINE_FIELDS, TOTAL_FIELDS, Invoice

Scalar = str | float | int | None


def flatten(invoice: Invoice | dict[str, Any]) -> dict[str, Scalar]:
    data = invoice.model_dump() if isinstance(invoice, Invoice) else invoice
    flat: dict[str, Scalar] = {}
    header = data.get("header") or {}
    for name in HEADER_FIELDS:
        flat[f"header.{name}"] = header.get(name)
    for index, item in enumerate(data.get("line_items") or []):
        for name in LINE_FIELDS:
            flat[f"line_items.{index}.{name}"] = item.get(name)
    totals = data.get("totals") or {}
    for name in TOTAL_FIELDS:
        flat[f"totals.{name}"] = totals.get(name)
    return flat


def field_name(path: str) -> str:
    """'line_items.3.rate' -> 'rate'; 'header.supplier_gstin' -> 'supplier_gstin'."""
    return path.rsplit(".", 1)[-1]


def generic_path(path: str) -> str:
    """'line_items.3.rate' -> 'line_items.*.rate' (used to aggregate metrics per field)."""
    parts = path.split(".")
    if parts[0] == "line_items" and len(parts) == 3:
        return f"line_items.*.{parts[2]}"
    return path


def line_index(path: str) -> int | None:
    parts = path.split(".")
    if parts[0] == "line_items" and len(parts) == 3:
        return int(parts[1])
    return None


def set_path(data: dict[str, Any], path: str, value: Scalar) -> None:
    """Set a value inside a nested invoice dict by dotted path (used when merging repairs)."""
    parts = path.split(".")
    if parts[0] == "line_items":
        items = data.setdefault("line_items", [])
        index = int(parts[1])
        while len(items) <= index:
            items.append(dict.fromkeys(LINE_FIELDS))
        items[index][parts[2]] = value
        return
    data.setdefault(parts[0], {})[parts[1]] = value
