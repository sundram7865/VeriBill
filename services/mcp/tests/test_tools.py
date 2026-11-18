import asyncio

import httpx
import pytest

from veribill_mcp import tools
from veribill_mcp.api_client import ApiClient, ApiConfig, ApiError

INVOICE = {
    "documentId": "doc-1",
    "invoiceNumber": "INV-1",
    "invoiceDate": "2026-03-15",
    "supplierName": "Kaveri Steel Pvt Ltd",
    "supplierGstin": "27AAPFU0939F1ZV",
    "grandTotal": 1180.0,
    "approvedVia": "auto",
    "lineItems": [],
}


def make_client(seen: list[httpx.Request]) -> ApiClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/api/invoices":
            return httpx.Response(200, json={"items": [INVOICE]})
        if request.url.path == "/api/invoices/missing":
            return httpx.Response(
                404, json={"error": {"code": "not_found", "message": "Invoice not found"}}
            )
        if request.url.path == "/api/review-tasks":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "t1",
                            "type": "audit",
                            "documentId": "doc-1",
                            "openedAt": "2026-11-01",
                            "document": {"originalName": "a.pdf", "documentConfidence": 0.97},
                        }
                    ]
                },
            )
        if request.url.path == "/api/metrics":
            return httpx.Response(200, json={"autoApprovalRate": 0.5})
        return httpx.Response(404, json={"error": {"code": "not_found", "message": "no route"}})

    config = ApiConfig("http://api.test/api", "read-only-token")
    return ApiClient(config, transport=httpx.MockTransport(handler))


def test_search_sends_filters_and_token_and_only_gets():
    seen: list[httpx.Request] = []
    result = tools.search_invoices(make_client(seen), supplier="Kaveri", min_amount=1000)
    assert result == [
        {
            k: INVOICE[k]
            for k in (
                "documentId",
                "invoiceNumber",
                "invoiceDate",
                "supplierName",
                "supplierGstin",
                "grandTotal",
                "approvedVia",
            )
        }
    ]
    request = seen[0]
    assert request.method == "GET"
    assert request.headers["authorization"] == "Bearer read-only-token"
    assert request.url.params["supplier"] == "Kaveri"
    assert "maxAmount" not in request.url.params  # None filters are not sent


def test_review_queue_is_reshaped_for_the_model():
    queue = tools.list_review_queue(make_client([]), kind="audit")
    assert queue == [
        {
            "task_id": "t1",
            "type": "audit",
            "document_id": "doc-1",
            "file": "a.pdf",
            "document_confidence": 0.97,
            "opened_at": "2026-11-01",
        }
    ]


def test_api_errors_are_readable():
    with pytest.raises(ApiError, match="Invoice not found"):
        tools.get_invoice(make_client([]), "missing")


def test_metrics_pass_through():
    assert tools.get_metrics(make_client([]), days=7) == {"autoApprovalRate": 0.5}


def test_missing_configuration_is_explained(monkeypatch):
    monkeypatch.delenv("VERIBILL_API_URL", raising=False)
    monkeypatch.delenv("VERIBILL_MCP_TOKEN", raising=False)
    with pytest.raises(ApiError, match="VERIBILL_MCP_TOKEN"):
        ApiConfig.from_env()


def test_server_exposes_exactly_the_four_read_only_tools():
    from veribill_mcp.server import mcp

    listed = asyncio.run(mcp.list_tools())
    names = sorted(t.name for t in listed)
    assert names == ["get_invoice", "get_metrics", "list_review_queue", "search_invoices"]
    for tool in listed:
        annotations = tool.annotations.model_dump(by_alias=True) if tool.annotations else {}
        assert annotations.get("readOnlyHint") is True
