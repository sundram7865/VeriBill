"""Builds one synthetic invoice: ground-truth values with correct GST arithmetic."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from evals.generator.catalog import (
    ITEMS,
    LOCATIONS,
    NAME_HEADS,
    NAME_MIDS,
    NAME_TAILS,
    STREETS,
    CatalogItem,
)
from evals.generator.gstin_factory import random_gstin
from extractor.data.states import state_names

CENT = Decimal("0.01")


@dataclass(frozen=True)
class InvoiceSpec:
    intra_state: bool
    n_items: int
    with_discount: bool
    with_round_off: bool
    reference_date: date


@dataclass
class SyntheticInvoice:
    ground_truth: dict
    supplier_address: str
    buyer_address: str
    supply_state_code: str
    notes: list[str] = field(default_factory=list)


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _company_name(rng: random.Random) -> str:
    return f"{rng.choice(NAME_HEADS)} {rng.choice(NAME_MIDS)} {rng.choice(NAME_TAILS)}"


def _address(rng: random.Random, location: tuple[str, str, str]) -> str:
    state_code, city, pin_prefix = location
    pin = f"{pin_prefix}{rng.randint(1, 99):03d}"
    street = f"No. {rng.randint(1, 250)}, {rng.choice(STREETS)}"
    return f"{street}, {city}, {state_names()[state_code]} - {pin}"


def _invoice_number(rng: random.Random, invoice_date: date) -> str:
    fy = invoice_date.year if invoice_date.month >= 4 else invoice_date.year - 1
    serial = rng.randint(1, 9999)
    patterns = (
        f"INV/{fy}-{(fy + 1) % 100:02d}/{serial:04d}",
        f"GST-{serial:05d}",
        f"A{rng.randint(100, 999)}{serial:04d}",
        f"{fy}/TX/{serial}",
    )
    return rng.choice(patterns)


def _quantity(rng: random.Random, item: CatalogItem) -> Decimal:
    if item.unit in ("HRS", "TRIP"):
        return Decimal(rng.randint(1, 24))
    if item.unit in ("KG", "MTR"):
        return Decimal(rng.choice([10, 25, 50, 75, 100, 120, 250])) + Decimal(
            rng.choice(["0", "0", "0.5"])
        )
    return Decimal(rng.choice([1, 2, 3, 4, 5, 6, 10, 12, 20, 24]))


def _line(rng: random.Random, item: CatalogItem, intra: bool, with_discount: bool) -> dict:
    quantity = _quantity(rng, item)
    rate = Decimal(rng.randint(item.min_rate, item.max_rate)) + Decimal(rng.choice(["0", "0.50"]))
    gross = _money(quantity * rate)
    discount = Decimal("0")
    if with_discount and rng.random() < 0.5:
        discount = _money(gross * Decimal(rng.choice(["0.02", "0.05", "0.10"])))
    taxable = gross - discount
    line = {
        "description": item.description,
        "hsn_sac": item.hsn_sac,
        "quantity": float(quantity),
        "unit": item.unit,
        "rate": float(rate),
        "discount": float(discount) if with_discount else None,
        "taxable_value": float(taxable),
        "cgst_rate": None,
        "cgst_amount": None,
        "sgst_rate": None,
        "sgst_amount": None,
        "igst_rate": None,
        "igst_amount": None,
    }
    if intra:
        half = Decimal(item.gst_rate) / 2
        tax = _money(taxable * half / 100)
        line.update(cgst_rate=float(half), cgst_amount=float(tax))
        line.update(sgst_rate=float(half), sgst_amount=float(tax))
    else:
        tax = _money(taxable * item.gst_rate / 100)
        line.update(igst_rate=float(item.gst_rate), igst_amount=float(tax))
    return line


def _totals(lines: list[dict], with_round_off: bool) -> dict:
    subtotal = sum(Decimal(str(line["taxable_value"])) for line in lines)
    tax_fields = ("cgst_amount", "sgst_amount", "igst_amount")
    total_tax = sum(Decimal(str(line[f])) for line in lines for f in tax_fields if line[f])
    exact = subtotal + total_tax
    if with_round_off:
        grand = exact.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        round_off: float | None = float(grand - exact)
    else:
        grand, round_off = exact, None
    return {
        "subtotal": float(subtotal),
        "total_tax": float(total_tax),
        "round_off": round_off,
        "grand_total": float(grand),
    }


def _pick_locations(rng: random.Random, intra: bool) -> tuple[tuple, tuple]:
    supplier = rng.choice(LOCATIONS)
    same = [loc for loc in LOCATIONS if loc[0] == supplier[0]]
    other = [loc for loc in LOCATIONS if loc[0] != supplier[0]]
    return supplier, rng.choice(same if intra else other)


def build_invoice(rng: random.Random, spec: InvoiceSpec) -> SyntheticInvoice:
    supplier_loc, buyer_loc = _pick_locations(rng, spec.intra_state)
    invoice_date = spec.reference_date - timedelta(days=rng.randint(3, 400))
    items = rng.sample(ITEMS, spec.n_items)
    lines = [_line(rng, item, spec.intra_state, spec.with_discount) for item in items]
    header = {
        "supplier_name": _company_name(rng),
        "supplier_gstin": random_gstin(rng, supplier_loc[0]),
        "buyer_name": _company_name(rng),
        "buyer_gstin": random_gstin(rng, buyer_loc[0]),
        "invoice_number": _invoice_number(rng, invoice_date),
        "invoice_date": invoice_date.isoformat(),
        "place_of_supply": state_names()[buyer_loc[0]],
        "currency": "INR",
    }
    return SyntheticInvoice(
        ground_truth={
            "header": header,
            "line_items": lines,
            "totals": _totals(lines, spec.with_round_off),
        },
        supplier_address=_address(rng, supplier_loc),
        buyer_address=_address(rng, buyer_loc),
        supply_state_code=buyer_loc[0],
    )
