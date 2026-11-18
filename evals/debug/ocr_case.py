"""Debug helper: show OCR lines and grounding failures for one case.
python -m evals.debug.ocr_case c0066"""

import sys

from evals.extractors.oracle_client import ground_truth_as_raw
from evals.manifest import load_suite
from extractor.grounding.ground import ground_invoice
from extractor.pipeline.ingest import ingest
from extractor.pipeline.normalize_raw import normalize_raw
from extractor.pipeline.parse import ParseOptions, parse_document

case_id = sys.argv[1]
case = next(c for c in load_suite().cases if c.case_id == case_id)
data = case.file.read_bytes()
kind = ingest(data, 10 * 1024 * 1024, 20).kind
doc = parse_document(data, kind, ParseOptions())
print(case.template, case.variant, [p for p in doc.pages])
for line in doc.lines[:45]:
    print(repr(line.text))
invoice, _ = normalize_raw(ground_truth_as_raw(case.ground_truth))
for path, g in ground_invoice(invoice, doc).items():
    if not g.found:
        print("NOT FOUND", path, g.score)
