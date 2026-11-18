"""Few-shot hints from past reviewer corrections, matched by exact supplier GSTIN.

The extractor stays stateless: the API sends corrections for the tenant's known suppliers, and
we pick the ones whose GSTIN is actually printed on this document (found by regex, not by LLM).
"""

from __future__ import annotations

import re

from extractor.normalize import normalize_gstin
from extractor.schemas.contract import FewShotSupplier

GSTIN_TOKEN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
MAX_EXAMPLES = 8


def gstins_in_text(text: str) -> set[str]:
    return {normalize_gstin(m) for m in GSTIN_TOKEN.findall(text.upper())}


def select_examples(text: str, suppliers: list[FewShotSupplier]) -> list[dict]:
    if not suppliers:
        return []
    present = gstins_in_text(text)
    for supplier in suppliers:
        if normalize_gstin(supplier.supplier_gstin) in present:
            return [c.model_dump() for c in supplier.corrections[:MAX_EXAMPLES]]
    return []
