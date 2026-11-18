# Setup: every key and one-time console setting you must provide

Nothing below is needed to build the project or run its tests: those use the fake/replay LLM
clients and the local storage driver. You need these to (1) run real extractions, (2) store files in
Cloudinary, and (3) deploy to AWS.

## 1. Gemini API (default LLM, free tier)

| What | Where it goes | Notes |
|---|---|---|
| `GEMINI_API_KEY` | `.env` (local), `/opt/invoiceiq/.env` (server), GitHub secret `GEMINI_API_KEY` (live eval workflow) | Free: sign in at aistudio.google.com → **Get API key** → create a key. No card needed for the free tier. |
| `LLM_PROVIDER` | same files | `gemini` (default) or `openai`. |
| `EXTRACT_MODEL`, `REPAIR_MODEL` | same files; optionally GitHub *variables* of the same names | Default `gemini-3.5-flash-lite` (DECISIONS D-035): stable, structured outputs, on the free tier. `gemini-3.8-flash` is a stronger free option for `REPAIR_MODEL`. |
| `LLM_REASONING_EFFORT` | same files | Gemini thinking level: `none`/`low`/`medium`/`high` (default `low`). |
| `LLM_BILLING_TIER` | same files | `free` records free-tier Gemini calls at $0; set `paid` once billing is enabled so cost estimates use `pricing.json`. |
| `LLM_DAILY_BUDGET_USD` | same files | Hard spend cap counted in Redis (matters on the paid tier); the extractor refuses work after it. |
| `services/extractor/pricing.json` | repo | Paid-tier prices and the list of free-tier models; update if Google changes them. |

**Free-tier caveats, read before using real invoices:**
- Google's pricing page says free-tier prompts and responses **are used to improve Google's products**.
  That is fine for this repo's synthetic invoices, but enable billing (paid tier) before processing real
  customer invoices.
- Free-tier quotas (requests per minute/day) apply per project; see your live limits at
  aistudio.google.com → Rate limits. The client retries 429s with exponential backoff, and a 150-case
  eval needs roughly 150–450 requests.

**OpenAI (optional alternative):** set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `LLM_BILLING_TIER=paid`
and an OpenAI model id (e.g. `gpt-6-luna`, see D-007).

## 2. Cloudinary (file storage)

1. Create a free account at cloudinary.com. From the dashboard copy **Cloud name**, **API key**, **API secret**.
2. Put them in `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` and set
   `STORAGE_DRIVER=cloudinary` (production compose always uses Cloudinary).
3. Console → Settings → **Security**: enable **"Allow delivery of PDF and ZIP files"**. Free accounts
   block PDF delivery by default; without this, downloads of uploaded PDFs can fail with 401/404.
4. Nothing else: files are uploaded as `raw` + `authenticated` assets under random ids in
   `CLOUDINARY_FOLDER` (default `invoiceiq`), and are only fetched server-side with 2-minute signed
   links. Use a different folder per environment (e.g. `invoiceiq-dev`).
5. Verify after deploying: upload one invoice in the UI, then open it in the review screen. If the
   document ends as `failed` with "Cloudinary download failed with HTTP 401", recheck step 3.

## 3. AWS (one EC2 instance, nothing else)

1. New account → enable MFA on the root user, create an IAM user or use IAM Identity Center for daily
   work, and set a **budget alert** (Billing → Budgets, e.g. $1) so free-plan credits can't surprise you.
2. EC2 → Launch instance (region **ap-south-1 Mumbai** recommended):
   - Ubuntu Server 24.04 LTS, instance type **t3.small** if shown as free-tier eligible on your account
     (otherwise t3.micro; see DECISIONS D-030), 20 GB gp3 root volume.
   - Key pair: create one, keep the `.pem` safe.
   - Security group: inbound **22** from *your IP only*, **80** and **443** from anywhere. Nothing else.
3. Elastic IPs → allocate one and associate it with the instance (free while attached to a running
   instance; release it if you stop using the instance).
4. DNS: create an **A record** for your domain (e.g. `invoices.example.com`) pointing at the Elastic IP.
   Any registrar works; a free subdomain service also works for a demo.
5. Then follow docs/DEPLOY.md.

## 4. GitHub

| What | Where | Notes |
|---|---|---|
| Push the repo | github.com | CI (`ci.yml`) runs on every push and pull request. |
| GHCR images | automatic | `images.yml` pushes `ghcr.io/<owner>/invoiceiq-{api,extractor,nginx}` with the built-in `GITHUB_TOKEN`. Make the three packages **public** (Package settings → Change visibility) or give the server a token with `read:packages` (`GHCR_USER`/`GHCR_TOKEN` env when running `deploy.sh`). |
| `GEMINI_API_KEY` secret | Settings → Secrets and variables → Actions | Only for the manual `eval-live` workflow (or `OPENAI_API_KEY` with variable `LLM_PROVIDER=openai`). |

## 5. Secrets you generate yourself

```bash
openssl rand -hex 32   # JWT_ACCESS_SECRET
openssl rand -hex 32   # EXTRACTOR_SERVICE_TOKEN (shared by the worker and the extractor)
openssl rand -hex 24   # POSTGRES_PASSWORD
```
Plus `SEED_ADMIN_PASSWORD` and `SEED_REVIEWER_PASSWORD` for the demo users created by
`scripts/deploy.sh --seed`. Never commit any of them; `.env` files are git-ignored.

## 6. MCP server (optional, local)

`pnpm --filter @invoiceiq/api mint:mcp-token -- <user email> 30` prints a 30-day read-only token. Put
it in `INVOICEIQ_MCP_TOKEN` with `INVOICEIQ_API_URL` (see services/mcp/README.md).
