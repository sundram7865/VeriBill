"""Node 6, repair: re-read only the failing fields, with the validator messages as hints.

Bounded: the graph calls this at most MAX_REPAIR_ATTEMPTS times per document.
"""

from __future__ import annotations

from extractor.grounding.ground import Grounding
from extractor.llm.base import LLMClient, LLMRequest, LLMResponse
from extractor.normalize import values_equal
from extractor.parsing.document import ParsedDocument
from extractor.prompts import REPAIR_SYSTEM, build_repair_user
from extractor.schemas.invoice import LINE_FIELDS
from extractor.schemas.paths import flatten, set_path
from extractor.schemas.raw import RepairResponse
from extractor.validators.issue import Issue

MAX_FIELDS_PER_REPAIR = 30

# A failed check implicates every field that feeds it, not just the one it is attached to.
_TOTALS = ["totals.subtotal", "totals.total_tax", "totals.round_off", "totals.grand_total"]
_LINE_TAXES = ["cgst_rate", "cgst_amount", "sgst_rate", "sgst_amount", "igst_rate", "igst_amount"]


def _line_paths(index: int, names: list[str]) -> list[str]:
    return [f"line_items.{index}.{name}" for name in names]


def related_paths(issue: Issue, n_lines: int) -> list[str]:
    parts = issue.path.split(".")
    index = int(parts[1]) if parts[0] == "line_items" else None
    if issue.code == "grand_total_mismatch":
        return _TOTALS
    if issue.code == "subtotal_mismatch":
        return ["totals.subtotal", *[f"line_items.{i}.taxable_value" for i in range(n_lines)]]
    if issue.code == "total_tax_mismatch":
        amounts = ["cgst_amount", "sgst_amount", "igst_amount"]
        return ["totals.total_tax", *[p for i in range(n_lines) for p in _line_paths(i, amounts)]]
    if issue.code == "line_taxable_mismatch" and index is not None:
        return _line_paths(index, ["quantity", "rate", "discount", "taxable_value"])
    if issue.code == "line_tax_mismatch" and index is not None:
        return _line_paths(index, ["taxable_value", *_LINE_TAXES])
    if issue.code.startswith("tax_type") and index is not None:
        return ["header.place_of_supply", "header.supplier_gstin", *_line_paths(index, _LINE_TAXES)]
    return [issue.path]


def is_repairable(issue: Issue) -> bool:
    """Errors, plus values the document does not seem to contain. Plain warnings are not
    worth a model call (e.g. a missing HSN code is usually genuinely missing)."""
    return issue.severity == "error" or issue.code == "not_grounded"


def repair_targets(issues: list[Issue], n_lines: int) -> dict[str, str]:
    """path -> reason, for every field the repair call should re-read."""
    targets: dict[str, str] = {}
    for issue in issues:
        if not is_repairable(issue):
            continue
        for path in related_paths(issue, n_lines):
            targets.setdefault(path, issue.message)
    return dict(list(targets.items())[:MAX_FIELDS_PER_REPAIR])


def region_text(document: ParsedDocument, grounding: dict[str, Grounding], paths: list[str]) -> str:
    """The pages that hold the fields in question: where they were found, plus page 1 for
    header fields and the last page for totals. Falls back to the whole document."""
    pages: set[int] = set()
    last_page = max((p.number for p in document.pages), default=1)
    for path in paths:
        found = grounding.get(path)
        if found and found.page:
            pages.add(found.page)
        elif path.startswith("header."):
            pages.add(1)
        elif path.startswith("totals."):
            pages.add(last_page)
    lost_line_item = any(
        p.startswith("line_items.") and not (grounding.get(p) and grounding[p].found) for p in paths
    )
    if not pages or lost_line_item:
        return document.layout_text
    return "\n".join(document.page_text(page) for page in sorted(pages))


def request_repair(
    client: LLMClient,
    model: str,
    raw: dict,
    targets: dict[str, str],
    document_text: str,
    reasoning_effort: str | None,
    temperature: float | None,
) -> LLMResponse:
    current = flatten(raw)
    fields = [
        {"path": p, "value": current.get(p), "reason": reason} for p, reason in targets.items()
    ]
    request = LLMRequest(
        purpose="repair",
        model=model,
        system=REPAIR_SYSTEM,
        user=build_repair_user(fields, document_text),
        schema=RepairResponse,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
    )
    return client.complete(request)


def _valid_target(path: str, n_lines: int) -> bool:
    parts = path.split(".")
    if parts[0] == "line_items":
        return (
            len(parts) == 3
            and parts[1].isdigit()
            and int(parts[1]) < n_lines
            and (parts[2] in LINE_FIELDS)
        )
    return True


def merge_repair(
    raw: dict, targets: dict[str, str], response: RepairResponse, n_lines: int
) -> tuple[dict, dict[str, str]]:
    """Apply returned values for requested paths only; report confirmed vs changed per path."""
    merged = {
        "header": dict(raw["header"]),
        "line_items": [dict(item) for item in raw["line_items"]],
        "totals": dict(raw["totals"]),
    }
    before = flatten(raw)
    outcomes: dict[str, str] = {}
    for field in response.fields:
        if field.path not in targets or not _valid_target(field.path, n_lines):
            continue  # the model may only touch what we asked about
        set_path(merged, field.path, field.value)
        same = values_equal(field.path, before.get(field.path), field.value)
        outcomes[field.path] = "confirmed" if same else "changed"
    return merged, outcomes
