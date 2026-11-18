"""The single LangGraph graph: a mostly linear pipeline with one bounded repair loop.

ingest -> parse -> extract -> ground -> validate -> decide -> END
             \\                  ^          |
              \\                 |          v
               \\               ground <- repair   (at most max_repair_attempts times)
                \\-> decide (unreadable: nothing to extract)
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from extractor.pipeline.nodes import (
    decide_node,
    extract_node,
    ground_node,
    ingest_node,
    needs_repair,
    parse_node,
    repair_node,
    validate_node,
)
from extractor.pipeline.state import PipelineDeps, PipelineState


def _after_parse(state: PipelineState) -> str:
    return "decide" if state["document"].is_empty else "extract"


def build_graph(deps: PipelineDeps):
    graph = StateGraph(PipelineState)
    for name, node in (
        ("ingest", ingest_node),
        ("parse", parse_node),
        ("extract", extract_node),
        ("ground", ground_node),
        ("validate", validate_node),
        ("repair", repair_node),
        ("decide", decide_node),
    ):
        graph.add_node(name, partial(node, deps=deps))

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "parse")
    graph.add_conditional_edges("parse", _after_parse, {"extract": "extract", "decide": "decide"})
    graph.add_edge("extract", "ground")
    graph.add_edge("ground", "validate")
    graph.add_conditional_edges(
        "validate",
        lambda state: "repair" if needs_repair(state, deps) else "decide",
        {"repair": "repair", "decide": "decide"},
    )
    graph.add_edge("repair", "ground")  # re-normalise, re-ground and re-validate the merge
    graph.add_edge("decide", END)
    return graph.compile()


def run_graph(state: PipelineState, deps: PipelineDeps) -> PipelineState:
    # Each repair visit runs repair -> ground -> validate (3 steps); leave generous headroom.
    limit = 20 + 3 * deps.max_repair_attempts
    return build_graph(deps).invoke(state, config={"recursion_limit": limit})
