"""Phase 2 runner: the nodes in a straight line, no repair loop.

Kept as the reference behaviour: graph.run_graph(max_repairs=0) must produce the same result
(tested in tests/test_graph.py).
"""

from __future__ import annotations

from extractor.pipeline.nodes import (
    decide_node,
    extract_node,
    ground_node,
    ingest_node,
    parse_node,
    validate_node,
)
from extractor.pipeline.state import PipelineDeps, PipelineState


def run_plain(state: PipelineState, deps: PipelineDeps) -> PipelineState:
    for node in (ingest_node, parse_node):
        state = {**state, **node(state, deps)}
    if not state["document"].is_empty:
        for node in (extract_node, ground_node, validate_node):
            state = {**state, **node(state, deps)}
    return {**state, **decide_node(state, deps)}
