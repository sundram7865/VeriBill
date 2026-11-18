"""Builds an extractor adapter by name. Imports are lazy so 'dummy' needs no pipeline deps."""

from __future__ import annotations

from evals.extractors.base import Extractor
from evals.manifest import Suite

EXTRACTORS = ("dummy", "oracle", "pipeline")


def build_extractor(name: str, suite: Suite, max_repairs: int, threshold: float) -> Extractor:
    if name == "dummy":
        from evals.extractors.dummy import DummyExtractor

        return DummyExtractor()
    if name == "oracle":
        from evals.extractors.pipeline import PipelineExtractor

        return PipelineExtractor(suite, max_repairs, threshold, oracle=True)
    if name == "pipeline":
        from evals.extractors.pipeline import PipelineExtractor

        return PipelineExtractor(suite, max_repairs, threshold, oracle=False)
    raise ValueError(f"unknown extractor '{name}', expected one of {EXTRACTORS}")
