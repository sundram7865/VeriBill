# Evals

```bash
python -m evals.generate                      # 150 seeded synthetic cases -> evals/fixtures/generated/
python -m evals.run --extractor dummy         # harness sanity check (scores ~0)
python -m evals.run --extractor oracle        # LLM replaced by ground truth: measures the rest
EVAL_MODE=record OPENAI_API_KEY=... EXTRACT_MODEL=gpt-6-luna REPAIR_MODEL=gpt-6-luna \
  python -m evals.run --extractor pipeline    # live model, responses saved to evals/llm_cache/
EVAL_MODE=replay python -m evals.run --extractor pipeline   # offline replay of the recordings
python -m evals.report <results.json> [--before <results-r0.json>]   # tables for EVAL_REPORT.md
python -m evals.compare --baseline evals/baseline.json --current <results.json>
python -m evals.gate                          # CI: oracle run + compare against baseline.json
```

OCR cases need the `tesseract` binary. On a machine without it, use the eval image:
`docker compose --profile eval run --rm evals --extractor oracle` (on Windows Git Bash prefix
`MSYS_NO_PATHCONV=1`).

Layout: `generator/` (templates, degradation, tricky cases), `metrics/` (field matching, P/R/F1,
routing, thresholds), `extractors/` (dummy, oracle, pipeline adapters), `fixtures/` (generated suite,
exported corrections, dedupe test vectors), `results/` (run outputs; `baseline.json` is the gate's reference).

Never fabricate recordings: `evals/llm_cache/` must only ever contain responses written by record mode.
