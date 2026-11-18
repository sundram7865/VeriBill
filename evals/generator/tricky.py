"""Deliberately broken or adversarial variants. Ground truth always equals what is printed.

The extractor should read these values faithfully; the validators should then flag them.
"""

from __future__ import annotations

import random

from evals.generator.catalog import INJECTION_NOTES
from evals.generator.factory import SyntheticInvoice
from evals.generator.gstin_factory import corrupt_check_character


def wrong_grand_total(invoice: SyntheticInvoice, rng: random.Random) -> list[str]:
    totals = invoice.ground_truth["totals"]
    delta = rng.choice([-1, 1]) * rng.randint(50, 5000)
    totals["grand_total"] = round(totals["grand_total"] + delta, 2)
    return ["totals.grand_total"]


def wrong_subtotal(invoice: SyntheticInvoice, rng: random.Random) -> list[str]:
    totals = invoice.ground_truth["totals"]
    delta = rng.choice([-1, 1]) * rng.randint(100, 3000)
    totals["subtotal"] = round(totals["subtotal"] + delta, 2)
    return ["totals.subtotal", "totals.grand_total"]


def invalid_gstin(invoice: SyntheticInvoice, rng: random.Random) -> list[str]:
    header = invoice.ground_truth["header"]
    header["supplier_gstin"] = corrupt_check_character(header["supplier_gstin"], rng)
    return ["header.supplier_gstin"]


def prompt_injection(invoice: SyntheticInvoice, rng: random.Random) -> list[str]:
    invoice.notes.append(rng.choice(INJECTION_NOTES))
    return []


MUTATIONS = {
    "wrong_grand_total": wrong_grand_total,
    "wrong_subtotal": wrong_subtotal,
    "invalid_gstin": invalid_gstin,
    "prompt_injection": prompt_injection,
}
