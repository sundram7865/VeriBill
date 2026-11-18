"""Run the pipeline on one file from the command line.

    python -m extractor.cli invoice.pdf [--mode live|record|replay] [--max-repairs 2]
                                        [--plain] [--reference-date 2026-11-01]

Needs EXTRACT_MODEL and, for live/record, GEMINI_API_KEY (or OPENAI_API_KEY with
LLM_PROVIDER=openai). Prints the response JSON.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from extractor.config import load_settings
from extractor.llm.base import LLMError
from extractor.llm.factory import MODES, build_llm_client
from extractor.pipeline.ingest import IngestError
from extractor.pipeline.parse import ParseError
from extractor.schemas.contract import ExtractMetadata
from extractor.service import deps_from_settings, run_extraction


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("file", type=Path)
    parser.add_argument("--mode", choices=MODES, default=None)
    parser.add_argument("--max-repairs", type=int, default=None)
    parser.add_argument("--plain", action="store_true", help="run without the LangGraph graph")
    parser.add_argument("--reference-date", default=None, help="treat this date as today")
    args = parser.parse_args()

    settings = load_settings()
    if args.max_repairs is not None:
        settings = replace(settings, max_repair_attempts=args.max_repairs)
    metadata = ExtractMetadata(
        document_id=args.file.stem,
        attempt=1,
        filename=args.file.name,
        reference_date=args.reference_date,
    )
    try:
        deps = deps_from_settings(settings, build_llm_client(settings, args.mode))
        result = run_extraction(args.file.read_bytes(), metadata, deps, use_graph=not args.plain)
    except (IngestError, ParseError, LLMError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
