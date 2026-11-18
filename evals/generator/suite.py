"""The synthetic suite plan: which template, variant and trick each of the ~150 cases gets."""

from __future__ import annotations

import copy
import hashlib
import random
from dataclasses import dataclass, field
from datetime import date

import pymupdf

from evals.generator.degrade import SCAN_VARIANTS, degrade
from evals.generator.factory import InvoiceSpec, SyntheticInvoice, build_invoice
from evals.generator.formatting import format_place
from evals.generator.render import render_pdf
from evals.generator.templates import TEMPLATES, TEMPLATES_BY_NAME, Template
from evals.generator.tricky import MUTATIONS

DEV_SHARE_PERCENT = 60


@dataclass(frozen=True)
class CasePlan:
    case_id: str
    template: str
    variant: str  # "digital" or one of SCAN_VARIANTS
    trick: str | None = None
    duplicate_of: str | None = None


@dataclass
class GeneratedCase:
    plan: CasePlan
    file_bytes: bytes
    mime: str
    pages: int
    ground_truth: dict
    expected_issue_paths: list[str] = field(default_factory=list)


def split_for(case_id: str) -> str:
    bucket = int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16) % 100
    return "dev" if bucket < DEV_SHARE_PERCENT else "test"


def plan_suite() -> list[CasePlan]:
    """150 cases: 65 clean digital, 45 scans, 10 each of wrong totals, invalid GSTIN,
    prompt injection and duplicates."""
    plans: list[CasePlan] = []

    def add(template: str, variant: str, trick: str | None = None, dup: str | None = None):
        plans.append(CasePlan(f"c{len(plans) + 1:04d}", template, variant, trick, dup))

    names = [t.name for t in TEMPLATES]
    for i in range(65):
        add(names[i % 5], "digital")
    for i in range(45):
        # Rotate templates across variants (i // 5 shifts them each round) so a variant's
        # results are not secretly one template's results.
        add(names[(i + i // 5) % 5], SCAN_VARIANTS[i % 5])
    tricks = ["wrong_grand_total", "wrong_subtotal"] * 5 + ["invalid_gstin"] * 10
    tricks += ["prompt_injection"] * 10
    for i, trick in enumerate(tricks):
        variant = "scan_clean" if i % 4 == 3 else "digital"
        add(names[(i + 1) % 5], variant, trick)
    for i in range(10):
        base = plans[i * 6]  # an earlier clean digital case
        other_template = names[(names.index(base.template) + 2) % 5]
        add(other_template, SCAN_VARIANTS[i % 5], "duplicate", base.case_id)
    return plans


def _spec(rng: random.Random, template: Template, reference_date: date) -> InvoiceSpec:
    n_items = rng.randint(7, 12) if template.name == "statement" else rng.randint(1, 10)
    return InvoiceSpec(
        intra_state=rng.random() < 0.5,
        n_items=n_items,
        with_discount=template.supports_discount and rng.random() < 0.5,
        with_round_off=template.supports_round_off and rng.random() < 0.7,
        reference_date=reference_date,
    )


def _apply_template_formats(invoice: SyntheticInvoice, template: Template) -> None:
    """Ground truth holds text fields exactly as this template prints them."""
    header = invoice.ground_truth["header"]
    header["place_of_supply"] = format_place(invoice.supply_state_code, template.style)


def _page_count(pdf_bytes: bytes) -> int:

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        return doc.page_count


def generate_case(
    plan: CasePlan,
    seed: int,
    reference_date: date,
    base_invoices: dict[str, SyntheticInvoice],
) -> GeneratedCase:
    rng = random.Random(f"{seed}:{plan.case_id}")
    template = TEMPLATES_BY_NAME[plan.template]
    if plan.duplicate_of:
        invoice = copy.deepcopy(base_invoices[plan.duplicate_of])
    else:
        invoice = build_invoice(rng, _spec(rng, template, reference_date))
        base_invoices[plan.case_id] = copy.deepcopy(invoice)
    _apply_template_formats(invoice, template)

    expected: list[str] = []
    if plan.trick in MUTATIONS:
        expected = MUTATIONS[plan.trick](invoice, rng)

    pdf_bytes = render_pdf(invoice, template)
    pages = _page_count(pdf_bytes)
    if plan.variant == "digital":
        file_bytes, mime = pdf_bytes, "application/pdf"
    else:
        file_bytes, mime = degrade(pdf_bytes, plan.variant, rng)
    return GeneratedCase(plan, file_bytes, mime, pages, invoice.ground_truth, expected)
