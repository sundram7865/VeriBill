"""Typed pipeline state shared by the plain runner and the LangGraph graph."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TypedDict

from extractor.grounding.ground import Grounding
from extractor.llm.base import LLMClient
from extractor.llm.pricing import Pricing
from extractor.parsing.document import ParsedDocument
from extractor.pipeline.llm_calls import CallUsage
from extractor.schemas.contract import ExtractMetadata
from extractor.schemas.invoice import Invoice
from extractor.validators.issue import Issue


@dataclass(frozen=True)
class PipelineDeps:
    client: LLMClient
    pricing: Pricing
    extract_model: str
    repair_model: str
    reasoning_effort: str | None
    temperature: float | None
    max_file_bytes: int
    max_pages: int
    ocr_dpi: int
    min_text_chars_per_page: int
    ocr_lang: str
    ocr_remove_lines: bool
    max_repair_attempts: int
    auto_approve_threshold: float
    max_invoice_age_days: int
    amount_tolerance: float


class PipelineState(TypedDict, total=False):
    # inputs
    file_bytes: bytes
    metadata: ExtractMetadata
    today: date
    # ingest / parse
    file_kind: str
    page_count: int
    document: ParsedDocument
    # extraction (raw = as printed strings; invoice = normalised, typed)
    raw: dict
    first_pass_raw: dict
    invoice: Invoice
    normalization_issues: list[Issue]
    # grounding, validation, repair
    grounding: dict[str, Grounding]
    issues: list[Issue]
    repair_attempts: int
    repair_outcomes: dict[str, str]
    # decision and bookkeeping
    field_confidence: dict[str, float]
    document_confidence: float
    decision: str
    decision_reason: str
    required_grounded: bool
    calls: list[CallUsage]
    timings: dict[str, int]
