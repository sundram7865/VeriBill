"""Oracle LLM client for offline evals: answers with the ground truth.

This is NOT a model and its numbers are NOT extraction accuracy. It replaces only the LLM, so a
run with it measures everything else: parsing/OCR, grounding, validators, routing and latency.
Results produced with it are always labelled "oracle".
"""

from __future__ import annotations

import re

from extractor.llm.base import LLMRequest, LLMResponse
from extractor.schemas.field_types import FieldType, field_type
from extractor.schemas.paths import flatten

_REPAIR_LINE = re.compile(r"^- (\S+): current value", re.MULTILINE)


def _as_printed(path: str, value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        if field_type(path) == FieldType.NUMBER:
            return f"{value:g}"
        return f"{value:.2f}"
    return str(value)


def ground_truth_as_raw(ground_truth: dict) -> dict:
    def convert(section: dict, prefix: str) -> dict:
        return {k: _as_printed(f"{prefix}.{k}", v) for k, v in section.items()}

    return {
        "header": convert(ground_truth["header"], "header"),
        "line_items": [convert(item, "line_items.0") for item in ground_truth["line_items"]],
        "totals": convert(ground_truth["totals"], "totals"),
    }


class OracleLLMClient:
    def __init__(self, ground_truth: dict):
        self.raw = ground_truth_as_raw(ground_truth)
        self.flat = flatten(self.raw)

    def complete(self, request: LLMRequest) -> LLMResponse:
        if request.purpose == "repair":
            paths = _REPAIR_LINE.findall(request.user)
            data = {"fields": [{"path": p, "value": self.flat.get(p)} for p in paths]}
        else:
            data = self.raw
        return LLMResponse(
            data=request.schema.model_validate(data).model_dump(),
            model="oracle",
            tokens_in=0,
            tokens_out=0,
        )
