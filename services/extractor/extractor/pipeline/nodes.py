"""Pipeline nodes. Each takes the state (and deps) and returns only the keys it changes.

The same functions run in the plain sequential runner and inside the LangGraph graph.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps

from extractor.grounding.ground import ground_invoice
from extractor.pipeline.confidence import document_confidence, field_confidences
from extractor.pipeline.decide import decide
from extractor.pipeline.extract import extract_raw
from extractor.pipeline.few_shot import select_examples
from extractor.pipeline.ingest import ingest
from extractor.pipeline.llm_calls import usage_of
from extractor.pipeline.normalize_raw import normalize_raw
from extractor.pipeline.parse import ParseOptions, parse_document
from extractor.pipeline.repair import (
    is_repairable,
    merge_repair,
    region_text,
    repair_targets,
    request_repair,
)
from extractor.pipeline.state import PipelineDeps, PipelineState
from extractor.pipeline.validate import collect_issues
from extractor.schemas.invoice import empty_invoice
from extractor.schemas.paths import flatten
from extractor.schemas.raw import RepairResponse
from extractor.validators.runner import ValidationConfig

Node = Callable[[PipelineState, PipelineDeps], dict]


def timed(name: str) -> Callable[[Node], Node]:
    """Adds the node's wall time (ms) to state['timings'], summing repeated visits."""

    def decorator(fn: Node) -> Node:
        @wraps(fn)
        def wrapper(state: PipelineState, deps: PipelineDeps) -> dict:
            started = time.perf_counter()
            update = fn(state, deps)
            timings = dict(state.get("timings", {}))
            timings[name] = timings.get(name, 0) + round((time.perf_counter() - started) * 1000)
            return {**update, "timings": timings}

        return wrapper

    return decorator


@timed("ingest")
def ingest_node(state: PipelineState, deps: PipelineDeps) -> dict:
    result = ingest(state["file_bytes"], deps.max_file_bytes, deps.max_pages)
    return {"file_kind": result.kind, "page_count": result.page_count}


@timed("parse")
def parse_node(state: PipelineState, deps: PipelineDeps) -> dict:
    options = ParseOptions(
        dpi=deps.ocr_dpi,
        min_chars=deps.min_text_chars_per_page,
        lang=deps.ocr_lang,
        remove_lines=deps.ocr_remove_lines,
    )
    document = parse_document(state["file_bytes"], state["file_kind"], options)
    return {"document": document}


@timed("extract")
def extract_node(state: PipelineState, deps: PipelineDeps) -> dict:
    text = state["document"].layout_text
    examples = select_examples(text, state["metadata"].few_shot)
    response = extract_raw(
        deps.client, deps.extract_model, text, examples, deps.reasoning_effort, deps.temperature
    )
    calls = [*state.get("calls", []), usage_of("extract", response, deps.pricing)]
    return {
        "raw": response.data,
        "first_pass_raw": response.data,
        "calls": calls,
        "repair_attempts": 0,
        "repair_outcomes": {},
    }


@timed("ground")
def ground_node(state: PipelineState, deps: PipelineDeps) -> dict:
    invoice, normalization_issues = normalize_raw(state["raw"])
    grounding = ground_invoice(invoice, state["document"])
    return {
        "invoice": invoice,
        "normalization_issues": normalization_issues,
        "grounding": grounding,
    }


@timed("validate")
def validate_node(state: PipelineState, deps: PipelineDeps) -> dict:
    config = ValidationConfig(
        today=state["today"],
        max_invoice_age_days=deps.max_invoice_age_days,
        amount_tolerance=deps.amount_tolerance,
    )
    issues = collect_issues(
        state["invoice"], state["grounding"], state["normalization_issues"], config
    )
    return {"issues": issues}


@timed("repair")
def repair_node(state: PipelineState, deps: PipelineDeps) -> dict:
    n_lines = len(state["raw"]["line_items"])
    targets = repair_targets(state["issues"], n_lines)
    document_text = region_text(state["document"], state["grounding"], list(targets))
    response = request_repair(
        deps.client,
        deps.repair_model,
        state["raw"],
        targets,
        document_text,
        deps.reasoning_effort,
        deps.temperature,
    )
    merged, outcomes = merge_repair(
        state["raw"], targets, RepairResponse.model_validate(response.data), n_lines
    )
    # A later repair overrides an earlier outcome for the same field.
    all_outcomes = {**state.get("repair_outcomes", {}), **outcomes}
    calls = [*state.get("calls", []), usage_of("repair", response, deps.pricing)]
    return {
        "raw": merged,
        "repair_outcomes": all_outcomes,
        "calls": calls,
        "repair_attempts": state.get("repair_attempts", 0) + 1,
    }


@timed("decide")
def decide_node(state: PipelineState, deps: PipelineDeps) -> dict:
    document = state["document"]
    invoice = state.get("invoice") or empty_invoice()
    issues = state.get("issues", [])
    grounding = state.get("grounding", {})
    confidences = field_confidences(
        flatten(invoice), grounding, issues, state.get("repair_outcomes", {})
    )
    doc_conf = document_confidence(confidences)
    decision = decide(
        issues, grounding, doc_conf, deps.auto_approve_threshold, unreadable=document.is_empty
    )
    return {
        "field_confidence": confidences,
        "document_confidence": doc_conf,
        "decision": decision.route,
        "decision_reason": decision.reason,
        "required_grounded": decision.required_grounded,
    }


def needs_repair(state: PipelineState, deps: PipelineDeps) -> bool:
    attempts = state.get("repair_attempts", 0)
    return attempts < deps.max_repair_attempts and any(
        is_repairable(i) for i in state.get("issues", [])
    )
