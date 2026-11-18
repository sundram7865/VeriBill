# VeriBill MCP server (read-only)

Four tools over stdio, all backed by GET requests to the API with a read-only token:

| Tool | What it returns |
|---|---|
| `list_review_queue(kind?, limit?)` | open review tasks (needs_review / audit), oldest first |
| `get_invoice(document_id)` | the approved, normalised invoice |
| `search_invoices(supplier?, date_from?, date_to?, min_amount?, max_amount?, limit?)` | approved invoices |
| `get_metrics(days?)` | auto-approval rate, audited accuracy, correction rate, cost, latency |

There are no write or approve tools, and the token cannot write even if a tool tried: the API rejects
non-GET requests for `scope: mcp:read` tokens with 403.

## Run

```bash
pip install -r services/mcp/requirements.txt
pnpm --filter @veribill/api mint:mcp-token -- reviewer@demo.veribill.test 30   # prints a token
export VERIBILL_API_URL=http://127.0.0.1:4000/api
export VERIBILL_MCP_TOKEN=<token>
cd services/mcp && python -m veribill_mcp.server
```

Client configuration (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "veribill": {
      "command": "python",
      "args": ["-m", "veribill_mcp.server"],
      "cwd": "/path/to/VeriBill/services/mcp",
      "env": { "VERIBILL_API_URL": "http://127.0.0.1:4000/api", "VERIBILL_MCP_TOKEN": "<token>" }
    }
  }
}
```

Tests: `pytest services/mcp/tests` (uses `httpx.MockTransport`, no running API needed).
