"""Writes the JSON Schemas of the /v1/extract contract to services/extractor/contract/.

    python -m extractor.contract_export          # regenerate
    python -m extractor.contract_export --check  # fail if the committed files are stale

The API's contract test (apps/api/test/unit/extractorContract.test.ts) compares these files
with the Zod schemas, so a change on either side that the other has not followed fails CI.
"""

from __future__ import annotations

import argparse
import json
import sys

from extractor.config import SERVICE_DIR
from extractor.schemas.contract import ExtractMetadata, ExtractResponse

CONTRACT_DIR = SERVICE_DIR / "contract"
SCHEMAS = {
    "extract_metadata.schema.json": ExtractMetadata,
    "extract_response.schema.json": ExtractResponse,
}


def render(model) -> str:
    return (
        json.dumps(model.model_json_schema(mode="serialization"), indent=2, sort_keys=True) + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    CONTRACT_DIR.mkdir(exist_ok=True)
    stale = []
    for name, model in SCHEMAS.items():
        path = CONTRACT_DIR / name
        content = render(model)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(name)
        else:
            path.write_text(content, encoding="utf-8")
    if stale:
        print(f"stale contract files: {stale}; run python -m extractor.contract_export")
        sys.exit(1)


if __name__ == "__main__":
    main()
