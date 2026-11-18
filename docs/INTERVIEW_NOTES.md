# Interview notes

## 30-second pitch

InvoiceIQ reads Indian GST invoices (PDFs and scans) and turns them into structured data you can
trust. An LLM reads each invoice once and returns what is printed; deterministic rules then check
it: GSTIN checksums, CGST/SGST vs IGST, line and total arithmetic, dates. Every value has to be
found again in the document's words, with a page and a box. Only documents that pass everything
with high confidence are auto-approved; everything else goes to a review screen where a human sees
the highlighted source, fixes fields and approves. Those corrections become labelled data. The whole
thing is measured by a seeded eval suite of 150 synthetic invoices, including scans, broken totals,
invalid GSTINs, duplicates and prompt-injection text.

## 2-minute walkthrough

1. **Upload** (Next.js static export → Express): the API checks magic bytes, size and pages, hashes
   the bytes (exact duplicates are refused), stores the file as a private Cloudinary asset and
   enqueues a BullMQ job. The browser never sees a storage URL.
2. **Worker** downloads the bytes and calls the Python extractor over the private Docker network
   (`POST /v1/extract`, service token). The extractor never touches the database or Cloudinary.
3. **Pipeline** (one LangGraph graph): ingest → parse (PyMuPDF text layer, or Tesseract for scans, with
   table rules erased first) → extract (one structured-output call; strings as printed) → normalise
   (code parses numbers/dates) → ground (find every value: page + bbox) → validate → repair at most twice
   on failing fields only → decide (confidence from grounding, OCR, validators, repair agreement).
4. **Persist** in one transaction: run (unique on document+attempt, so retries are idempotent), fields,
   duplicate check on (GSTIN, invoice number, total), then either an invoice record (auto-approved, 10%
   sampled into audits) or a review task.
5. **Review**: split pane, boxes on the document, fields with confidence badges and validator messages,
   keyboard shortcuts. Approve/reject in one transaction that stores before/after corrections.
6. **Measure**: metrics page (auto-approval rate, audited accuracy, correction rate, validator catch
   rate, cost, p50/p95), the offline eval gate in CI, and corrections exported back into the eval suite.

## Per component: why, alternatives, what broke

### Monorepo and scaffold
- Why: Node owns the product (auth, tenants, state, queue); Python owns the AI pipeline; one HTTP
  contract between them, checked by a Pydantic↔Zod contract test.
- Rejected: one Python backend (same shape as SupportPilot); one Node backend (PyMuPDF, Tesseract and
  LangGraph are Python-first).
- What broke: npm "latest" was a new major for several packages (TypeScript 7, Prisma 8 RC); I pinned the
  latest stable of majors I can explain (D-003). `mcp` 2.x removed FastMCP, so I used `fastmcp` (D-006).
  Docker Desktop hung building every image in parallel on a 4 GB VM; building one at a time worked.

### Eval harness (built before the pipeline)
- Why: the brief says measure first. A seeded fpdf2 generator gives 150 cases with exact ground truth:
  5 templates, 6 variants (digital + 5 scan degradations), wrong totals, invalid GSTINs, duplicates and
  prompt injection. Ground truth is always what is *printed*, so the extractor is judged on reading and
  the validators on catching.
- Metrics: normalised exact match per field, P/R/F1 (a wrong value counts as one FP and one FN),
  fully-correct documents, auto-approval rate vs accuracy of auto-approved, validator catch rate and
  false-alarm rate, injection resistance, duplicate-key agreement, cost, p50/p95.
- Rejected: hand-labelled real invoices (privacy, and the brief forbids it); fabricating LLM recordings
  for CI (never; replay only replays real responses).
- What broke: Pillow's `effect_noise` uses C's RNG, so "seeded" noise wasn't reproducible; noise now
  comes from `random.Random(seed).randbytes`. Long descriptions overflowed table columns; cells now
  shrink text to fit. Worst one: the first plan confounded scan variant with template (every low-res
  scan was the same template), so "low-res accuracy" was really "modern-template accuracy". I caught it
  while explaining an odd ablation result and regenerated the suite with templates rotated (D-034).

### Extraction: LLM reads, code interprets
- The model returns strings exactly as printed (`RawInvoice`). Code parses "1,23,456.00", "15-Mar-2026",
  "9%" and flags anything unparseable (D-017). The system prompt forbids following instructions in the
  document, the text is wrapped in `<document>` delimiters, and output is schema-validated twice.
- Rejected: typed LLM output (the LLM would be doing format conversion the rules can do), letting the
  model compute totals.

### Grounding
- Type-aware matching (numbers must parse equal, names fuzzy ≥ 0.85, GSTINs tolerate one OCR
  confusion), row anchoring (a line item's numbers are searched on its description's line) and position
  preference (totals near the end). An ungrounded value is either hallucinated or lost by OCR: either way
  a human should see it.
- What broke: the first oracle run showed scanned gridded tables losing *every* line item. Tesseract
  treated the grid as an image. I added ruling-line removal using Pillow box-downscaling (no OpenCV); the
  first version damaged letter stems (OCR confidence fell 0.92 → 0.61 on one case), so the window was
  lengthened and the ink threshold raised. A later ablation showed it still hurt upscaled low-res scans
  (stems stretched by upscaling); cleaning now happens at native resolution, before upscaling. The
  ablation in EVAL_REPORT.md measures the effect with the feature on and off.

### Validators
- Pure functions, each unit-tested: GSTIN format + official state codes (from the GST e-invoice master,
  stored in one JSON file) + check character (test vector 27AAPFU0939F1ZV), tax type, line math, totals
  with a ₹1 tolerance, date window, invoice-number rule 46 format, HSN/SAC lengths.
- Duplicate detection lives in the API because the API owns the database.

### LangGraph graph
- One graph, typed state, one bounded loop (validate → repair → ground → validate, max 2). The same node
  functions run in a plain sequential runner; a test asserts the graph with 0 repairs equals it.
- Repair asks for the *related* fields of a failed check (a total mismatch re-reads subtotal, tax,
  round-off and total) and only sends the relevant pages. A changed value keeps a 0.75 confidence factor:
  disagreement between passes is a reason to look.
- Rejected: an agent that decides what to do next (unbounded cost and behaviour), multi-agent frameworks.

### LLM layer, cost and budget
- One `LLMClient` interface with live, record, replay and fake implementations. Replay is keyed by a hash
  of model + prompts + schema + settings, so any prompt change invalidates old recordings instead of
  silently reusing them. Cost comes from `pricing.json`; an unknown model costs NaN, not zero.
- Daily budget: spend counted in Redis per UTC day; over the cap the extractor returns 429 and the worker
  fails the document without retrying.

### Product backend
- Express 5 (async errors handled natively), Zod for every input, Prisma, BullMQ with exponential
  backoff. Every repository function takes `tenantId` first and asserts it; an integration test proves
  cross-tenant reads, writes and review submissions fail.
- Auth: 15-minute JWT access token in memory + opaque refresh token in an httpOnly, SameSite=Strict
  cookie, stored hashed, rotated on every refresh; replaying an old refresh token revokes the whole
  login family (tested).
- What broke: errors like "no API key" are 5xx but retrying cannot help; they are now non-retryable so
  a misconfigured deployment fails fast instead of looping.

### Web app
- Next.js static export served by Nginx: no Node in production. Query-string routes (`/review?id=`),
  TanStack Query with polling only while something is processing, react-pdf loaded client-only with the
  worker served from our own origin, boxes drawn from page-relative coordinates so they scale with zoom.
- Keyboard: j/k move, e edits, Esc stops, Ctrl+Enter approves, Shift+R rejects; letters never fire while
  typing in a field (unit-tested mapping).
- What broke: React 19's lint rules flagged setState inside an effect and ref writes during render;
  rewritten with `useMemo` for the object URL and an effect for the ref.

### Feedback loop
- Corrections store before/after and whether a validator had flagged the field (validator catch rate).
  `pnpm export:eval` turns approved documents into eval cases in the suite format. Few-shot hints for a
  supplier are matched by exact GSTIN found by regex in the document, so the extractor stays stateless.
  10% of auto-approved documents are sampled into audits by a deterministic hash.

### MCP server
- FastMCP over stdio, four read-only tools, annotated `readOnlyHint`. The token is a JWT with
  `scope: mcp:read`, and the API rejects every non-GET request for that scope, so the MCP server could
  not write even if someone added a tool.

### Deploy
- One EC2 instance, Docker Compose, images from GHCR, Nginx with Let's Encrypt (a temporary self-signed
  certificate breaks the chicken-and-egg problem), nightly `pg_dump` to EBS. No RDS, S3 or ElastiCache, so
  the Free Tier covers it.

## Likely interview questions

1. **Why not let the LLM return typed values and compute totals?**
   Arithmetic, checksums and date parsing are deterministic and testable; an LLM doing them adds a
   failure mode with no upside. The model's only job is reading. Keeping its output as printed strings
   also means the validators judge what the document says, so a wrong printed total is *flagged*, not
   silently "fixed" by the model.

2. **How do you know an auto-approved invoice is right?**
   Four layers: (a) every required field must be found in the document's words; (b) every validator must
   pass; (c) confidence from those signals must clear a threshold tuned on a dev split; (d) in production,
   10% of auto-approvals are audited by humans and the metrics page shows audited accuracy. Offline, the
   eval reports "auto-approved accuracy" and "flawed documents auto-approved" (see EVAL_REPORT.md).

3. **Why not use the model's confidence or logprobs?**
   Self-reported confidence is not calibrated, and the brief forbids relying on it. Each of my factors is
   observable and explainable to a reviewer: was it found, did OCR read it clearly, did a rule fail, did a
   second read agree.

4. **How do you handle prompt injection?**
   Document text is wrapped as data, the system prompt says never to follow it, the output must match a
   strict schema, and the decision is made by code. If the model were hijacked into returning a total of 0,
   the total check and grounding fail and the document goes to a human (tested in
   `test_pipeline.py::TestPromptInjection`; the eval has 10 injection cases).

5. **Why LangGraph for a mostly linear pipeline?**
   For exactly one thing: a bounded, inspectable loop (validate → repair → re-ground → re-validate, max 2)
   with typed state. It is a single graph, not an agent; every edge is deterministic. A test proves the
   graph with 0 repairs equals the plain sequential runner.

6. **How is tenant isolation enforced?**
   Every tenant-scoped table has `tenant_id`; every query goes through a repository function whose first
   argument is the tenant id and which asserts it is present; the tenant comes from the verified JWT, never
   from the request body. Integration tests prove cross-tenant reads, updates, file downloads and review
   submissions fail with 404 or no-ops.

7. **What happens if the worker crashes or a job is retried?**
   Job ids are `extract-<document>-<attempt>`, so double enqueues collapse. `extraction_runs` has a unique
   (document_id, attempt) index, so a retried job that already stored its run is a no-op, and a stale
   attempt is skipped. 5xx errors retry with exponential backoff; 4xx, the budget 429 and configuration
   errors fail immediately with a reason on the document.

8. **How do you control LLM cost?**
   One extraction call per document plus at most two small repair calls on failing fields only; a cheap
   default model; cost estimated per run from `pricing.json`; a hard daily cap in Redis; exact duplicate
   files are refused before any LLM call.

9. **You had no API key. What does the oracle eval actually tell you?**
   It replaces only the LLM with ground truth, so it measures everything else end to end on real PDFs and
   scans: OCR, grounding, validators, routing and non-LLM latency. It cannot tell you model accuracy;
   that is marked NOT MEASURED, with the exact command to produce it. It was still useful: it found that
   Tesseract dropped gridded tables, and the ablation showed my first fix hurt low-res scans.

10. **How do the Python and TypeScript sides stay in sync?**
    The Pydantic models export JSON Schemas into the repo; a Vitest test reduces both those and the Zod
    schemas to a canonical shape and compares them; a Python test fails if the exported files are stale.
    Changing one side without the other breaks CI.

11. **Why a static export behind Nginx instead of a Next.js server?**
    No SSR is needed (everything is behind login and fetched client-side), so production runs one less
    Node process on a small EC2 instance, and Nginx already terminates TLS and proxies /api.

12. **What would you change next?** See below.

## What I would change next

- Run the live eval (`eval-live.yml`), tune the auto-approve threshold on the dev split and report the
  held-out split; then replay the recordings in CI as a second gate.
- Better OCR for noisy scans: deskew, adaptive binarisation, 300 dpi for small fonts; measure each.
- Per-field thresholds (a wrong GSTIN costs more than a wrong unit), and letting reviewers add or delete
  line items.
- The pgvector experiment for unknown suppliers, only if the live eval shows few-shot hints help.
- Upgrade to the newer majors (TypeScript 7, Prisma 7) once typescript-eslint supports TS 7.
- Browser end-to-end tests (Playwright) for the review screen; today it is covered by unit tests, a
  static build and a manual test script.

## Resume bullets (measured numbers only)

1. Built **InvoiceIQ**, a multi-tenant GST-invoice extraction platform (Express, BullMQ, Postgres +
   FastAPI, LangGraph) where an LLM only reads and deterministic validators, grounding and a bounded
   repair loop decide; in a 150-invoice seeded eval with oracle extraction, validators caught **20/20**
   injected total and GSTIN-checksum errors with **0** flawed invoices auto-approved.
   *Reproduce:* `python -m evals.generate && python -m evals.run --extractor oracle --max-repairs 2`
   → `summary.validators.catch_rate`, `summary.routing.flawed_docs_auto_approved`.
   *Say in the interview:* the oracle replaces the LLM with ground truth, so this measures the rule layer,
   not the model; model accuracy was not measured (no API key during the build).

2. Found through an eval ablation that Tesseract dropped gridded tables on scanned invoices; a
   dependency-free ruling-line removal step raised grounded fields on 62 scanned invoices from
   **44.3% to 92.6%**, and a second ablation caught and fixed a regression it caused on low-resolution scans.
   *Reproduce:* `python -m evals.run --extractor oracle --variant scan` with `OCR_REMOVE_LINES=false`
   and `=true` → `summary.overall.grounded_field_rate` (EVAL_REPORT §4).

3. Shipped the product backend with JWT access tokens plus rotating, reuse-detecting refresh-token
   families, tenant-scoped repositories and idempotent BullMQ processing with retry classification,
   covered by **49** Vitest tests on real Postgres and Redis (cross-tenant isolation, retries, duplicate
   detection, audits) and a Pydantic↔Zod contract test.
   *Reproduce:* `docker compose up -d postgres redis && pnpm --filter @invoiceiq/api test` → "Tests 49 passed".
