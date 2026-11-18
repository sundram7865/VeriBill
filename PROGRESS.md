# PROGRESS

Checkpoint log so work can resume after a context reset. No git commits are made (owner override),
so this file is the record of what is done.

## Environment notes (this machine)

- Windows 11, Node 22.22, Python 3.12.6 venv at `.venv` (extractor installed editable, fastmcp added).
- pnpm 10.34.9 installed globally (owner approved). `pnpm install` took ~16 min here (Defender).
- Docker Desktop: ~3.9 GB VM, 1–2 min per container start. Building all images at once hung the
  daemon; build one service at a time. In Git Bash, prefix docker commands that use container paths
  with `MSYS_NO_PATHCONV=1`. Use `127.0.0.1`, not `localhost`, for host DB access.
- Tesseract is not installed on the host: OCR tests skip locally and run in the eval image
  (`invoiceiq-evals:latest`).
- Run Vitest from `/D/InvoiceIQ/...` (uppercase drive); lowercase `d:` made Vitest find no files.

## Phase 0 — Scaffold — done
- pnpm workspace, Python venv + pinned requirements, docker-compose.yml (postgres+pgvector, redis,
  extractor, migrate, api, worker, web, evals profile), health endpoints, CI, docs, CLAUDE.md,
  Prisma migration.

## Phase 1 — Eval harness — done
- Generator (5 templates × digital + 5 scan variants + tricky cases → 150 cases), metrics, runner,
  compare, gate, report, record/replay cache. Dummy extractor scored (recall 0.0).

## Phase 2/3 — Pipeline + LangGraph — done
- ingest/parse/extract/normalize/ground/validate/repair/decide/output, one LangGraph graph, FastAPI
  `/v1/extract`, CLI, contract export. Eval-driven fix: ruling-line removal before OCR (D-022).
- Offline (oracle) evals run in Docker; live-model numbers NOT MEASURED (no key).

## Phase 4 — Backend — done
- Prisma schema, auth (JWT + rotating refresh cookie), uploads → StorageProvider, BullMQ worker,
  duplicates, review/corrections, metrics, export, invoices search, scripts (seed, e2e, export:eval,
  mint:mcp-token). 49 Vitest tests on real Postgres + Redis pass.

## Phase 5 — Web — done
- Login, documents (upload, live status, export), queue, review (split pane, boxes, shortcuts),
  metrics. Static export builds (all routes static). Unit tests for pure helpers.

## Phase 6 — Feedback loop — done
- Corrections → eval cases (`pnpm export:eval`), deterministic 10% audit sampling, few-shot by GSTIN.
  pgvector experiment not run (needs live model).

## Phase 7 — MCP, deploy, docs — done
- FastMCP read-only server + tests; CI (lint/type/test, contract check, oracle eval gate in the eval
  image), GHCR image workflow, manual live-eval workflow; deploy files (compose.prod, nginx + TLS,
  bootstrap/deploy/TLS/backup scripts); README, ARCHITECTURE, DECISIONS (D-001..D-034), EVAL_REPORT,
  INTERVIEW_NOTES (pitch, walkthrough, Q&A, resume bullets), SETUP, DEPLOY, KNOWN_ISSUES, MANUAL_TEST.
- Final eval (regenerated suite, templates rotated across scan variants): see docs/EVAL_REPORT.md;
  `evals/baseline.json` = trimmed `oracle-all-r2.json`.
- Verified: 196 Python tests (+1 OCR test that passes in the eval image: 95 there), 49 API tests on real
  Postgres/Redis, 6 web tests, lint/format/typecheck clean, static web build, host end-to-end flow with a
  scratch oracle-backed extractor (not in repo).

## Open items
- Live-model numbers (needs a free GEMINI_API_KEY), real Cloudinary run, deploy to EC2: owner actions in SETUP.md.
- Docker stack verified healthy here (postgres, redis, extractor, api, worker); `pnpm e2e` reached the
  extractor and ended `failed: llm_not_configured` as expected without a key. Web dev image build timed out
  on this network (KNOWN_ISSUES #11). App containers were stopped afterwards (`docker compose up -d` restarts).
