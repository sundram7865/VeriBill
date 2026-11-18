"""One extraction, end to end: build the initial state, run the graph, shape the response."""

from __future__ import annotations

import time
from datetime import UTC, date, datetime

from extractor.config import Settings
from extractor.llm.base import LLMClient, LLMNotConfiguredError
from extractor.llm.pricing import Pricing
from extractor.pipeline.graph import run_graph
from extractor.pipeline.output import build_response
from extractor.pipeline.plain import run_plain
from extractor.pipeline.state import PipelineDeps, PipelineState
from extractor.schemas.contract import ExtractMetadata, ExtractResponse


def deps_from_settings(settings: Settings, client: LLMClient, **overrides) -> PipelineDeps:
    if not settings.extract_model:
        raise LLMNotConfiguredError("EXTRACT_MODEL is not set")
    values = {
        "client": client,
        "pricing": Pricing(settings.pricing_path, settings.billing_tier),
        "extract_model": settings.extract_model,
        "repair_model": settings.repair_model or settings.extract_model,
        "reasoning_effort": settings.reasoning_effort,
        "temperature": settings.temperature,
        "max_file_bytes": settings.max_file_bytes,
        "max_pages": settings.max_pages,
        "ocr_dpi": settings.ocr_dpi,
        "min_text_chars_per_page": settings.min_text_chars_per_page,
        "ocr_lang": settings.ocr_lang,
        "ocr_remove_lines": settings.ocr_remove_lines,
        "max_repair_attempts": settings.max_repair_attempts,
        "auto_approve_threshold": settings.auto_approve_threshold,
        "max_invoice_age_days": settings.max_invoice_age_days,
        "amount_tolerance": settings.amount_tolerance,
    }
    values.update(overrides)
    return PipelineDeps(**values)


def _today(metadata: ExtractMetadata) -> date:
    if metadata.reference_date:
        return date.fromisoformat(metadata.reference_date)
    return datetime.now(UTC).date()


def run_extraction(
    file_bytes: bytes, metadata: ExtractMetadata, deps: PipelineDeps, use_graph: bool = True
) -> ExtractResponse:
    started = time.perf_counter()
    state: PipelineState = {
        "file_bytes": file_bytes,
        "metadata": metadata,
        "today": _today(metadata),
        "timings": {},
        "calls": [],
    }
    final = run_graph(state, deps) if use_graph else run_plain(state, deps)
    latency_ms = round((time.perf_counter() - started) * 1000)
    return build_response(final, latency_ms)
