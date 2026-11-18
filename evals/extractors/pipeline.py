"""Runs the real extraction graph on each case, with either the oracle or the configured LLM."""

from __future__ import annotations

import os
import time
from dataclasses import replace

from evals.extractors.base import Prediction
from evals.extractors.oracle_client import OracleLLMClient
from evals.manifest import REPO_ROOT, Case, Suite
from extractor.config import load_settings
from extractor.llm.base import LLMError
from extractor.llm.factory import build_llm_client
from extractor.pipeline.ingest import IngestError
from extractor.pipeline.parse import ParseError
from extractor.schemas.contract import ExtractMetadata
from extractor.service import deps_from_settings, run_extraction

EVAL_CACHE_DIR = REPO_ROOT / "evals" / "llm_cache"


class PipelineExtractor:
    def __init__(self, suite: Suite, max_repairs: int, threshold: float, oracle: bool):
        self.name = "oracle" if oracle else "pipeline"
        self.suite, self.oracle = suite, oracle
        settings = load_settings()
        if oracle:
            # The oracle needs no model id; label it so cost and model fields are obviously fake.
            settings = replace(settings, extract_model="oracle", repair_model="oracle")
        else:
            settings = replace(settings, llm_cache_dir=EVAL_CACHE_DIR)
        self.settings = replace(
            settings, max_repair_attempts=max_repairs, auto_approve_threshold=threshold
        )
        mode = os.environ.get("EVAL_MODE", "replay")
        self.shared_client = None if oracle else build_llm_client(self.settings, mode)

    def _deps(self, case: Case):
        client = OracleLLMClient(case.ground_truth) if self.oracle else self.shared_client
        return deps_from_settings(self.settings, client)

    def predict(self, case: Case) -> Prediction:
        metadata = ExtractMetadata(
            document_id=case.case_id, attempt=1, reference_date=self.suite.reference_date
        )
        started = time.perf_counter()
        try:
            result = run_extraction(case.file.read_bytes(), metadata, self._deps(case))
        except (IngestError, ParseError, LLMError) as exc:
            return Prediction(
                invoice=None,
                decision="failed",
                error=f"{type(exc).__name__}: {exc}",
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        # Replayed calls take ~0 ms; add the latency recorded during the live run so p50/p95
        # reflect what production would see.
        replayed_ms = sum(c.latency_ms for c in result.llm_calls if c.from_cache)
        return Prediction(
            invoice=result.invoice.model_dump() if result.invoice else None,
            decision=result.decision,
            document_confidence=result.document_confidence,
            required_grounded=result.required_grounded,
            issues=[i.model_dump() for i in result.issues],
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms + replayed_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            repair_attempts=result.repair_attempts,
        )
