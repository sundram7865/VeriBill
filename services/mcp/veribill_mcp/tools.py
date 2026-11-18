"""Tool implementations as plain functions, so they can be tested without an MCP runtime."""

from __future__ import annotations

from veribill_mcp.api_client import ApiClient


def list_review_queue(api: ApiClient, kind: str | None = None, limit: int = 20) -> list[dict]:
    """Open review tasks, oldest first. kind: 'needs_review', 'audit' or None for both."""
    data = api.get("/review-tasks", {"status": "open", "type": kind, "limit": min(limit, 200)})
    return [
        {
            "task_id": t["id"],
            "type": t["type"],
            "document_id": t["documentId"],
            "file": t["document"]["originalName"],
            "document_confidence": t["document"]["documentConfidence"],
            "opened_at": t["openedAt"],
        }
        for t in data["items"]
    ]


def get_invoice(api: ApiClient, document_id: str) -> dict:
    """The approved, normalised invoice for a document (header, line items, totals)."""
    return api.get(f"/invoices/{document_id}")["invoice"]


def search_invoices(
    api: ApiClient,
    supplier: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    limit: int = 20,
) -> list[dict]:
    """Approved invoices filtered by supplier (name or GSTIN), date range and amount range."""
    data = api.get(
        "/invoices",
        {
            "supplier": supplier,
            "from": date_from,
            "to": date_to,
            "minAmount": min_amount,
            "maxAmount": max_amount,
            "limit": min(limit, 200),
        },
    )
    keep = (
        "documentId",
        "invoiceNumber",
        "invoiceDate",
        "supplierName",
        "supplierGstin",
        "grandTotal",
        "approvedVia",
    )
    return [{k: item[k] for k in keep} for item in data["items"]]


def get_metrics(api: ApiClient, days: int = 30) -> dict:
    """Auto-approval rate, audited accuracy, correction rate, cost and latency for the tenant."""
    return api.get("/metrics", {"days": days})
