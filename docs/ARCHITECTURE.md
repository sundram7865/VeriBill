# Architecture

**The LLM proposes, rules verify, humans handle the uncertain cases, and accuracy is measured.**

```mermaid
flowchart LR
  B[Browser<br/>Next.js static export] -->|HTTPS| N[Nginx<br/>static files + /api proxy + TLS]
  N -->|/api| A[API<br/>Express + Prisma + Zod]
  A --> P[(Postgres 16)]
  A -->|enqueue| R[(Redis<br/>BullMQ + rate limits + LLM budget)]
  A <-->|private assets| C[(Cloudinary)]
  W[Worker<br/>BullMQ consumer] --> R
  W <-->|download bytes| C
  W -->|POST /v1/extract<br/>file bytes + metadata<br/>service token, private network| X[Extractor<br/>FastAPI + LangGraph]
  X -->|structured outputs| O[OpenAI]
  X -->|daily spend counter| R
  W --> P
  M[MCP server<br/>stdio, read-only] -->|GET + read-only token| A
```

## Responsibilities

| Component | Owns | Never does |
|---|---|---|
| `apps/web` | Login, upload, document list, review screen, metrics, export | Talk to Cloudinary or the extractor |
| `apps/api` (server) | Auth, tenants, documents, review tasks, corrections, metrics, export, duplicate checks | Call the LLM |
| `apps/api` (worker) | Queue consumption, retries, Cloudinary download, persisting results | Serve HTTP (only a health probe) |
| `services/extractor` | The AI pipeline: parse, extract, ground, validate, repair, decide | Touch the database or Cloudinary |
| `services/mcp` | Read-only tools over the API | Write anything |

## Pipeline (one LangGraph graph)

```mermaid
flowchart LR
  I[ingest<br/>magic bytes, size, pages] --> PA[parse<br/>PyMuPDF text / Tesseract OCR<br/>words + boxes + layout text]
  PA -->|no text| D
  PA --> E[extract<br/>1 LLM call, strings as printed]
  E --> G[ground<br/>normalise + find each value<br/>page + bbox]
  G --> V[validate<br/>GSTIN, tax type, line math,<br/>totals, dates, identifiers]
  V -->|errors and attempts < 2| RP[repair<br/>re-read failing fields only]
  RP --> G
  V --> D[decide<br/>confidence from signals<br/>auto_approve / needs_review / reject]
```

- The model only **reads**: it returns strings exactly as printed (DECISIONS D-017). Code parses
  numbers and dates, checks GSTIN checksums, does all arithmetic and decides.
- Document text is untrusted: delimited as data, the system prompt forbids following it, the output is
  schema-validated, and validators plus grounding catch a hijacked answer (tested).
- Confidence = grounding × OCR × validator × repair-agreement factors (D-019); never the model's opinion.

## Document lifecycle

```mermaid
stateDiagram-v2
  [*] --> uploaded: POST /api/documents (validated, stored, queued)
  uploaded --> processing: worker picks the job
  processing --> auto_approved: decide = auto_approve and not a duplicate
  processing --> needs_review: errors, low confidence, ungrounded field, or duplicate
  processing --> rejected: unreadable
  processing --> failed: extractor error after retries / non-retryable error
  needs_review --> approved: reviewer approves (with corrections)
  needs_review --> rejected: reviewer rejects
  auto_approved --> auto_approved: audit sample approved (corrections update the invoice)
  failed --> uploaded: admin reprocesses
```

Every closed review stores corrections (`before`, `after`, `had_validator_issue`). They feed the
metrics page, `pnpm export:eval` (new eval cases) and few-shot hints for the same supplier GSTIN.

## Data model

`tenants`, `users` (admin | reviewer), `refresh_tokens` (rotation families), `documents`,
`extraction_runs` (unique document_id + attempt), `extracted_fields` (path, value, confidence, page,
bbox, issues), `review_tasks` (needs_review | audit), `corrections`, `invoices` (normalised approved
data), `suppliers`, `audit_log` (append-only). Every tenant-scoped table has `tenant_id`, and every
query goes through a repository function that takes a `tenantId` first
(`apps/api/src/modules/**/**.repository.ts`). `test/integration/tenantIsolation.test.ts` proves
cross-tenant reads and writes fail.

## Contracts between services

- `POST /v1/extract`: multipart `file` + `metadata` (JSON). Pydantic models in
  `services/extractor/extractor/schemas/contract.py`, mirrored in Zod in
  `apps/api/src/extractor/extractorSchemas.ts`. `python -m extractor.contract_export` writes the
  JSON Schemas to `services/extractor/contract/`; `apps/api/test/unit/extractorContract.test.ts`
  compares them with the Zod schemas, and a Python test checks the files are current.
- Error codes: 4xx and 429 (budget) are final; 5xx are retried with exponential backoff, except
  configuration errors (`llm_not_configured`, `llm_replay_miss`, `ocr_unavailable`).

## Where things are

| Concern | File |
|---|---|
| Validators | `services/extractor/extractor/validators/` |
| Grounding | `services/extractor/extractor/grounding/` |
| Graph | `services/extractor/extractor/pipeline/graph.py` |
| Prompts | `services/extractor/extractor/prompts.py` |
| LLM clients (live/record/replay/fake), budget, pricing | `services/extractor/extractor/llm/` |
| Queue + persistence | `apps/api/src/queue/` |
| Review + corrections | `apps/api/src/modules/review/` |
| Metrics SQL | `apps/api/src/modules/metrics/metrics.queries.ts` |
| Review screen | `apps/web/src/components/review/` |
| Eval harness | `evals/` |
| Deploy | `deploy/` |
