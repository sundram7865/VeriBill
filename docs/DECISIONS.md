# Decisions

Each entry: decision, alternatives considered, reason. Newest at the bottom.

## D-001 Keep the name InvoiceIQ
- Alternatives: rename (e.g. "GSTLens").
- Reason: the repo folder is already named InvoiceIQ and the name says what it does.

## D-002 No git commits during the build (owner override)
- Alternatives: conventional commit at the end of each phase (as the brief says).
- Reason: the owner said "don't commit or push anything for now". PROGRESS.md is the checkpoint record.

## D-003 Pin the latest stable release of majors I can explain, not every newest major
- Chosen: TypeScript 5.9.3, Prisma 6.19.3, BullMQ 5.81.5, ioredis 5.11.1, Vitest 3.2.7, ESLint 9.39.5,
  pino 9.14.0, Express 5.3.0, Zod 4.6.7, Next 16.4.6, React 19.3.1, Tailwind 4.3.5, react-pdf 10.5.0.
- Alternatives: TypeScript 7 (native compiler), Prisma 7/8 (driver adapters required, 8 is an RC),
  BullMQ 6, Vitest 5, ESLint 10.
- Reason: on 2026-11-18 npm "latest" for several packages was a new major (Prisma's latest tag even pointed
  at an RC). typescript-eslint does not support TypeScript 7's native API yet. Stable, well-documented majors
  keep the project explainable in an interview and keep CI green. Upgrading is listed in "what I would change next".

## D-004 API compiles to CommonJS with `module: NodeNext`
- Alternatives: native ESM ("type": "module", `.js` extensions on every relative import).
- Reason: fewer moving parts with Prisma 6 and jsonwebtoken; NodeNext still type-checks package exports maps.

## D-005 One Python virtualenv at the repo root
- Alternatives: one venv per service.
- Reason: evals import the extractor package directly (`pip install -e services/extractor`), so a single
  environment is simpler. Each service still has its own pinned requirements file for its Docker image.

## D-006 MCP server uses the standalone `fastmcp` package
- Alternatives: the official `mcp` SDK.
- Reason: `mcp` 2.x (current on 2026-11-18) renamed FastMCP to `MCPServer` and removed `mcp.server.fastmcp`.
  The brief asks for FastMCP, and the standalone `fastmcp` package keeps that API.

## D-007 Default LLM: `gpt-6-luna` for both EXTRACT_MODEL and REPAIR_MODEL
- Alternatives: gpt-5-nano ($0.05/$0.40 per 1M), gpt-5.6-luna ($0.20/$1.20), gpt-4o-mini ($0.15/$0.60),
  gpt-6.1-terra ($1/$5) as a stronger repair model.
- Reason: checked on OpenAI's official pricing and model pages on 2026-11-18. gpt-6-luna is the low-cost tier of
  the newest family ($0.10 input / $0.50 output per 1M tokens), lists structured outputs as supported, and has
  a large context window. A 2-page invoice prompt is roughly 2–4k input tokens, so cost per document is a
  fraction of a cent (the actual number is NOT MEASURED until a live eval runs). Model ids live only in env
  vars; prices live in services/extractor/pricing.json so they can be updated without code changes.

## D-008 Determinism: reasoning effort "low", no temperature by default, plus a record/replay cache
- Alternatives: temperature=0 always.
- Reason: gpt-6-luna is a reasoning model; its docs list `reasoning.effort` but do not promise `temperature`
  support, and sending an unsupported parameter fails the request. LLM_TEMPERATURE is honoured only when set
  (for non-reasoning models). Reproducibility for evals and CI comes from the replay cache keyed by prompt hash.

## D-009 The API's page-count check is a fast heuristic; the extractor's is authoritative
- Alternatives: add a PDF library to the API.
- Reason: the brief allows no extra PDF dependency in Node. The API rejects bad magic bytes and size, and counts
  `/Type /Page` objects as a fast pre-check. Compressed object streams can hide that count, so the extractor's
  ingest node (PyMuPDF) enforces the real 20-page limit and the document ends as `failed` with a clear reason.

## D-010 Two duplicate keys: `content_hash` (file bytes) and `dedupe_key` (invoice identity)
- Alternatives: only the invoice-level key from the brief.
- Reason: `content_hash` catches the same file uploaded twice before spending an LLM call; `dedupe_key`
  (sha256 of supplier GSTIN | normalized invoice number | grand total, as specified) catches a re-scan of the
  same invoice. `dedupe_key` is an added column on documents so unapproved documents can be compared too.

## D-011 `extraction_runs.attempt` is the processing attempt, not the repair attempt
- Alternatives: one row per repair attempt.
- Reason: the brief asks for idempotency on document id plus attempt. A unique (document_id, attempt) index makes
  a retried queue job unable to store the same run twice. Repair attempts happen inside one graph run and are
  recorded in `repair_attempts` and the result JSON.

## D-012 Refresh tokens are stored hashed in a `refresh_tokens` table with rotation families
- Alternatives: Redis keys; stateless refresh JWTs.
- Reason: rotation needs server-side state. A family id lets us detect reuse of an old token (likely theft) and
  revoke the whole login. Added table beyond the brief's list; it holds no invoice data.

## D-013 Password hashing with Node's built-in `crypto.scrypt`
- Alternatives: bcrypt/argon2 packages.
- Reason: not in the allowed stack, and scrypt is a memory-hard KDF built into Node.

## D-014 Rate limiting with a ~20-line Redis fixed-window limiter
- Alternatives: express-rate-limit.
- Reason: not in the allowed stack; Redis is already there and the logic is small enough to explain.

## D-015 Cloudinary files are `raw` + `authenticated`; downloads use short-lived signed API URLs
- Alternatives: `image` resource type (would allow transformations), `upload` type (public).
- Reason: `raw` means Cloudinary never transforms anything; `authenticated` means no unsigned URL works. The
  worker and the API download with `private_download_url` (expires in 2 minutes) and stream bytes to the
  browser, so browsers never see a Cloudinary URL.

## D-016 Offline evals use an "oracle" LLM client, clearly labelled
- Alternatives: report nothing offline; build a regex extractor baseline.
- Reason: there is no OpenAI key in this environment and recordings must never be fabricated. The oracle client
  returns the ground truth as if it were the model output, so the run measures everything except the LLM:
  parsing/OCR, grounding, validators, routing and non-LLM latency. Its numbers are always labelled "oracle"
  and are never presented as extraction accuracy. Live accuracy is NOT MEASURED until a key is provided.

## D-017 The LLM returns strings exactly as printed; code converts them
- Alternatives: ask the model for typed values (numbers, ISO dates).
- Reason: "do not let the LLM do what rules can do". The model only reads; `normalize_raw.py` parses
  "1,23,456.00", "15-Mar-2026" and "9%" deterministically, and an unparseable value becomes an issue
  instead of a silent guess. It also makes grounding fairer: we look for what was printed.

## D-018 Grounding is type-aware, row-anchored and position-aware
- Alternatives: plain fuzzy string search for every value.
- Reason: amounts, dates, GSTINs and state names each have many printed forms. Numbers must match
  exactly after parsing; names use a fuzzy ratio (>= 0.85); GSTINs/codes tolerate one OCR confusion.
  The same amount often appears twice (a line item and the total), so line-item fields prefer the
  visual line where that item's description was found, and totals prefer the end of the document.

## D-019 Confidence is computed from signals, never from the model
- Formula (pipeline/confidence.py): grounding score x OCR factor x validator factor x repair factor;
  document confidence = min(lowest required-field confidence, mean field confidence).
- Alternatives: model logprobs or self-reported confidence (the brief forbids relying on the latter).
- Reason: every factor is observable and explainable to a reviewer.

## D-020 Repair re-reads related fields, on the pages where they are
- A grand-total mismatch asks again for subtotal, total tax, round-off and grand total; a line-math
  error asks for that line's quantity, rate, discount and taxable value. The text sent is the pages
  holding those fields (page 1 for header, last page for totals), or the whole document if a line item
  was never located. Repair runs on errors and on "not_grounded" warnings only; at most 2 attempts.
- Reason: a failed check implicates its inputs, not just the field it is attached to.

## D-021 "reject" is only for unreadable documents; file problems are HTTP errors
- Ingest problems (wrong type, too big, too many pages, corrupt) return 422 and the document ends as
  `failed` with the reason. A readable file with no text at all is routed to `reject`.

## D-022 Table ruling lines are erased before OCR (found by the eval)
- The first oracle run showed scanned gridded tables losing every line item: Tesseract treated the grid
  as an image. `parsing/preprocess.py` finds long straight ink runs with Pillow box-downscaling (no
  OpenCV) and paints them white. Alternatives: OpenCV morphology (new dependency), different psm modes.
- Second iteration, also found by measurement: on low-resolution scans the image was upscaled *before*
  cleaning, which stretched letter stems towards the detection window and erased them (low-res
  auto-approvals fell from 6/11 to 0/11 in the ablation). Cleaning now runs at the image's native
  resolution, before upscaling, and the window is 60 px (85% ink) so even 2x-upscaled stems survive.
  `OCR_REMOVE_LINES=false` turns it off; EVAL_REPORT.md has the on/off ablation.

## D-034 Scan variants rotate through all templates
- The first suite plan gave each scan degradation exactly one template (all low-res scans were the
  "modern" template, all rotations "ledger"), so per-variant results were really per-template results.
  The plan now shifts the template every round (`names[(i + i // 5) % 5]`), so each variant covers all
  five templates. All published numbers come from the regenerated suite.

## D-023 Static export details
- Dev: `next dev` proxies /api to the API with a rewrite (only in development); prod: Nginx serves
  `out/` and proxies /api. The review screen is `/review?id=...` (no dynamic routes). pdf.js runs
  client-only (`next/dynamic`, `ssr: false`) and its worker file is copied into `public/` at install.

## D-024 Exact duplicate files are refused at upload
- `content_hash` match returns a per-file "duplicate_file" rejection with the existing document id,
  so the same PDF is never paid for twice. Re-scans with different bytes are caught later by `dedupe_key`.

## D-025 Few-shot from corrections stays stateless on the extractor side
- The worker sends up to 50 suppliers x 3 recent corrections, grouped by supplier GSTIN. The extractor
  finds GSTINs printed on the document by regex and uses only the exact match. Alternative: a second
  round trip or letting the extractor read the database (forbidden by the brief).

## D-026 Audit sampling is a deterministic hash of the document id
- `sha256(id) mod 10000 < rate x 10000`. Reproducible and testable, unlike Math.random().

## D-027 Two roles, minimal differences
- Both roles upload, review and see metrics. Only admins export data and reprocess documents.

## D-028 Reviewers edit existing fields; they cannot add or delete line items
- Simplest review model that still produces before/after labels. Logged in KNOWN_ISSUES.

## D-029 MCP authentication is a read-only JWT
- `pnpm mint:mcp-token -- <email>` signs a token with `scope: mcp:read`; the API rejects every
  non-GET request with that scope. The MCP server itself only issues GETs.

## D-030 Assumptions in place of the missing "section 10" (AWS + Cloudinary)
- One EC2 instance on a new account's free plan (accounts created after 2025-07-15 list t3.micro,
  t3.small, t4g.micro, t4g.small, c7i-flex.large and m7i-flex.large as eligible; checked 2026-11-18).
  Recommended: t3.small (2 GB) in ap-south-1 (Mumbai), Ubuntu 24.04, 20 GB gp3, 2 GB swap. The
  compose memory limits fit 1 GB + swap (t3.micro) at concurrency 1, slowly.
- Cloudinary free plan, private `authenticated` raw assets, one folder per environment.

## D-031 Threshold tuning needs the live model; the default stays 0.9 until then
- With the oracle client every extraction is correct, so accuracy is 1.0 at every threshold and the
  tuning rule ("lowest threshold whose dev auto-approved accuracy >= target") degenerates to the lowest
  threshold. That is not a real tuning result, so AUTO_APPROVE_THRESHOLD keeps its default of 0.9.
  `python -m evals.report` produces the dev/test table from a live run (EVAL_REPORT.md says how).

## D-032 The CI eval gate runs the oracle suite
- Deterministic and keyless, so it can run on every pull request and catches regressions in parsing,
  OCR, grounding, validators and routing. Model-quality regressions need the manual live workflow
  (`eval-live.yml`); its recordings can later be replayed offline.

## D-033 The optional pgvector experiment was not run
- It needs embeddings and extraction from a live model to show any effect; without an API key there is
  nothing honest to measure. pgvector stays unused (the image supports it). See EVAL_REPORT.md.
