# Eval report

Every number here comes from a run executed in this repository, with the command that reproduces it.
The exact result files behind the tables are kept in `evals/results/published/`.
Anything that needs a live model is marked **NOT MEASURED** with the command to run.

**Read this first:** no LLM API key was available while building, so all pipeline numbers below use
the **oracle** client. It answers every extraction and repair call with the ground truth, so field
accuracy is 1.0 by construction and says nothing about the model. What the oracle runs *do* measure,
on real PDFs and scans, is everything around the model: PDF text layer and Tesseract OCR, grounding
(finding each value again on the page), validators, routing, confidence and non-LLM latency.

## 1. The suite

`python -m evals.generate` (seed 20261118, reference date 2026-11-01). Deterministic: same seed, same
files and ground truth.

| | |
|---|---|
| Cases | 150 (dev split 88, held-out test split 62, by hash of the case id) |
| Templates | 5 layouts × 30 cases each (grid/no grid, 3 header layouts, 4 date formats, 3 amount formats) |
| Variants | 88 digital PDFs; scans: 18 clean, 11 rotated, 11 noisy, 11 blurred, 11 low-resolution (each scan variant spans all 5 templates) |
| Files | 99 PDF (incl. image-only scanned PDFs), 28 PNG, 23 JPEG; 122 one-page, 28 two-page |
| Invoices | 1–12 line items (mean 6.08); 86 intra-state (CGST+SGST), 64 inter-state (IGST); 43 with a discount column, 82 with round-off |
| Tricky cases | 5 wrong grand totals, 5 wrong subtotals, 10 invalid GSTIN check characters, 10 prompt-injection notes, 10 re-scans of earlier invoices (duplicates) |
| Ground truth | 10,404 non-empty field values; always what is *printed* (a wrong printed total is the ground truth, and validators must flag it) |

## 2. Harness sanity check (Phase 1)

`python -m evals.run --extractor dummy --out evals/results/phase1-dummy-all.json`

The dummy extractor returns an empty invoice: recall 0.0, F1 0.0, fully-correct documents 0.0,
auto-approval 0.0 over 150 cases. This is what an extractor that reads nothing should score.

## 3. Pipeline with the oracle client (Phase 2 baseline of everything except the model)

All runs were in the eval Docker image (Tesseract 5.3.0) on a Windows laptop under Docker Desktop,
with other work running at the same time, so latencies are indicative only.

```bash
python -m evals.run --extractor oracle --max-repairs 2 --threshold 0.9 --out evals/results/oracle-all-r2.json
python -m evals.run --extractor oracle --max-repairs 0 --threshold 0.9 --out evals/results/oracle-all-r0.json
python -m evals.report evals/results/oracle-all-r2.json --before evals/results/oracle-all-r0.json \
    --ablation-off evals/results/oracle-scans-no-line-removal.json
```
(on a machine without Tesseract, prefix with the eval image, see evals/README.md)

| Metric (150 cases) | Value | What it means |
|---|---|---|
| Field exact match / F1 / fully-correct documents | 1.000 / 1.000 / 1.000 | By construction (the oracle *is* the ground truth); confirms normalisation and scoring agree |
| Grounded fields (values found again in the document) | 0.969 | Digital PDFs 1.000; OCR misses on scans are the rest |
| Validator catch rate (20 flawed: 10 wrong totals, 10 invalid GSTINs) | 1.000 (20/20) | An error was raised at the expected field every time |
| Flawed documents auto-approved | 0 | None of the 20 slipped through |
| Validator false-alarm rate on clean documents | 0.092 (12/130) | All 12 are scans whose required field OCR could not confirm (`not_grounded`); conservative by design |
| Auto-approval rate (threshold 0.9) | 0.573 (86/150) | Digital 0.830; scans 0.000–0.455 depending on degradation |
| Accuracy of auto-approved documents | 1.000 | Trivial under the oracle; the live number is NOT MEASURED |
| Prompt-injection cases with the true grand total | 1.000 (10/10) | The pipeline doesn't break on injected notes; model behaviour is NOT MEASURED |
| Duplicate pairs with matching dedupe keys | 1.000 (10/10) | Re-scans of the same invoice produce the same key |
| Latency without the model, p50 / p95 | 702 ms / 6.1 s | Digital 327 ms / 1.0 s; scans (OCR) 2.1 s / 8.1 s |
| Failed documents | 0 | |

By split (threshold 0.9; the test split was never used for any decision):

| split | cases | fully correct | auto-approval | auto-approved accuracy | flawed auto-approved | validator catch rate | failed | p50 ms |
|---|---|---|---|---|---|---|---|---|
| dev | 88 | 1.000 | 0.534 | 1.000 | 0 | 1.000 | 0 | 962 |
| test | 62 | 1.000 | 0.629 | 1.000 | 0 | 1.000 | 0 | 489 |
| all | 150 | 1.000 | 0.573 | 1.000 | 0 | 1.000 | 0 | 719 |

(p50 differs slightly from the table above because this report recomputes it per split.)

By variant:

| variant | cases | grounded fields | auto-approval |
|---|---|---|---|
| digital | 88 | 1.000 | 0.830 |
| scan_blur | 11 | 0.968 | 0.455 |
| scan_clean | 18 | 0.989 | 0.111 |
| scan_lowres | 11 | 0.970 | 0.273 |
| scan_noise | 11 | 0.802 | 0.000 |
| scan_rotate | 11 | 0.864 | 0.273 |

Clean scans auto-approve rarely even though 98.9% of their values are found: OCR word confidence
(×(0.5 + 0.5 × confidence)) keeps their document confidence just under 0.9. Whether 0.9 is the right bar
can only be decided with real model errors (section 5).

## 4. Ablation: erasing table rules before OCR (DECISIONS D-022)

Same 62 scanned cases, line removal off (`OCR_REMOVE_LINES=false`) vs on:

```bash
OCR_REMOVE_LINES=false python -m evals.run --extractor oracle --variant scan \
    --out evals/results/oracle-scans-no-line-removal.json
```

| variant | cases | grounded fields, off | grounded fields, on | auto-approval, off | auto-approval, on |
|---|---|---|---|---|---|
| scan_blur | 11 | 0.366 | 0.968 | 0.182 | 0.455 |
| scan_clean | 18 | 0.477 | 0.989 | 0.111 | 0.111 |
| scan_lowres | 11 | 0.517 | 0.970 | 0.182 | 0.273 |
| scan_noise | 11 | 0.293 | 0.802 | 0.000 | 0.000 |
| scan_rotate | 11 | 0.526 | 0.864 | 0.273 | 0.273 |
| **all scans** | **62** | **0.443** (1,946 of 4,396 values) | **0.926** (4,070 of 4,396) | 9 / 62 | 13 / 62 |

Without it, Tesseract drops whole gridded tables. An earlier version of the fix (cleaning after
upscaling, 40 px window) *hurt* low-resolution scans; that was found by this same ablation and fixed by
cleaning at native resolution with a 60 px window (INTERVIEW_NOTES "Grounding").

## 5. Repair loop and threshold tuning (Phase 3)

Before vs after the repair loop, oracle client:

| run | max repairs | fully correct | auto-approval | validator catch rate |
|---|---|---|---|---|
| before | 0 | 1.000 | 0.573 | 1.000 |
| after | 2 | 1.000 | 0.573 | 1.000 |

Identical, as expected: the oracle never misreads, so a repair can only confirm the same value (58
documents used both repair attempts, all on genuinely flawed documents or OCR misses, and nothing
changed). The loop's value is fixing *model* misreads, which needs the live run (section 6).
`test_pipeline.py` proves the mechanics with a fake model: a misread total is fixed by repair, a value the
document doesn't contain is retried exactly twice and sent to review.

Threshold table (dev split used for the choice, test split reported):

| threshold | dev auto-approval | dev accuracy | test auto-approval | test accuracy |
|---|---|---|---|---|
| 0.50 | 0.784 | 1.000 | 0.774 | 1.000 |
| 0.60 | 0.750 | 1.000 | 0.742 | 1.000 |
| 0.70 | 0.739 | 1.000 | 0.710 | 1.000 |
| 0.75 | 0.727 | 1.000 | 0.710 | 1.000 |
| 0.80 | 0.682 | 1.000 | 0.710 | 1.000 |
| 0.85 | 0.636 | 1.000 | 0.710 | 1.000 |
| 0.90 | 0.534 | 1.000 | 0.629 | 1.000 |
| 0.95 | 0.420 | 1.000 | 0.581 | 1.000 |
| 0.98 | 0.420 | 1.000 | 0.581 | 1.000 |

The rule "lowest threshold with dev accuracy ≥ 0.98" picks 0.50 here, but only because the oracle is
always right, so that choice is meaningless and **not adopted**. AUTO_APPROVE_THRESHOLD stays at its
default of 0.9 until a live run provides real errors (DECISIONS D-031). The table does show the
trade-off the threshold controls: on the held-out split, lowering it from 0.9 to 0.5 would auto-approve
77% instead of 63%.

The CI gate (`python -m evals.gate`) re-runs this oracle suite on every pull request and fails if any
quality metric drops more than 0.02 below `evals/baseline.json` (a trimmed copy of `oracle-all-r2.json`).

## 6. Live model (gemini-3.5-flash-lite): NOT MEASURED

Needs a free `GEMINI_API_KEY` (aistudio.google.com). Reproduce with record mode (saves every response
for offline replay):

```bash
export LLM_PROVIDER=gemini GEMINI_API_KEY=... LLM_BILLING_TIER=free
export EXTRACT_MODEL=gemini-3.5-flash-lite REPAIR_MODEL=gemini-3.5-flash-lite LLM_REASONING_EFFORT=low
export EVAL_MODE=record
python -m evals.run --extractor pipeline --max-repairs 0 --out evals/results/live-r0.json   # before repair
python -m evals.run --extractor pipeline --max-repairs 2 --out evals/results/live-r2.json   # after repair
python -m evals.report evals/results/live-r2.json --before evals/results/live-r0.json
```
(Scans need Tesseract: run these through the eval image, or use the manual `eval-live` GitHub workflow.)

| Metric | Value |
|---|---|
| Field exact match, P/R/F1 per field | NOT MEASURED |
| Fully-correct documents | NOT MEASURED |
| Auto-approval rate and accuracy of auto-approved documents | NOT MEASURED |
| Repair loop gain (before vs after) | NOT MEASURED |
| Prompt-injection resistance of the model itself | NOT MEASURED (the oracle run shows only that the pipeline does not break) |
| Cost per document | $0 on the free tier by definition; paid-tier cost NOT MEASURED (paid price $0.30 / $2.50 per 1M input/output tokens) |
| p50/p95 latency including the model | NOT MEASURED |
| Tuned auto-approve threshold (dev) and its held-out result | NOT MEASURED (default 0.9 kept; see DECISIONS D-031) |

After a recorded run, `EVAL_MODE=replay` reproduces it offline at no cost.

## 7. Feedback-loop experiments (Phase 6)

- **Corrections as eval cases:** `pnpm export:eval` writes reviewed documents to
  `evals/fixtures/corrections/`, scored with `python -m evals.run --suite corrections --extractor pipeline`.
  No real review activity exists yet, so there is no corrections suite to report.
- **Few-shot from same-supplier corrections:** implemented and unit-tested; its effect on accuracy is
  NOT MEASURED (needs the live model and real corrections).
- **pgvector for unknown suppliers (optional):** not run, because it needs a live model to show any
  effect (DECISIONS D-033). pgvector stays unused.
