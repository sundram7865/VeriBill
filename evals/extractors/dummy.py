"""Dummy extractor: returns an empty invoice. Proves the harness scores a known-bad system."""

from __future__ import annotations

import time

from evals.extractors.base import Prediction
from evals.manifest import Case
from extractor.schemas.invoice import empty_invoice


class DummyExtractor:
    name = "dummy"

    def predict(self, case: Case) -> Prediction:
        started = time.perf_counter()
        invoice = empty_invoice().model_dump()
        return Prediction(
            invoice=invoice,
            decision="needs_review",
            latency_ms=(time.perf_counter() - started) * 1000,
        )
