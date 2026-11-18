import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from extractor.config import load_settings
from extractor.llm.base import BudgetExceededError
from extractor.llm.fake import FakeLLMClient
from extractor.main import create_app
from tests.factories import raw_dict
from tests.pdf_factory import invoice_pdf

TOKEN = "test-service-token-0123456789"
METADATA = json.dumps({"document_id": "doc-1", "attempt": 1, "reference_date": "2026-11-01"})


def client_with(llm) -> TestClient:
    settings = replace(
        load_settings(), service_token=TOKEN, extract_model="gpt-6-luna", repair_model="gpt-6-luna"
    )
    return TestClient(create_app(settings, llm))


def post(client: TestClient, data: bytes, token: str = TOKEN, metadata: str = METADATA):
    return client.post(
        "/v1/extract",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("invoice.pdf", data, "application/pdf")},
        data={"metadata": metadata},
    )


@pytest.fixture
def ok_client():
    return client_with(FakeLLMClient(lambda _r: raw_dict()))


def test_extract_happy_path(ok_client):
    response = post(ok_client, invoice_pdf())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"] == "auto_approve"
    assert body["document_id"] == "doc-1"
    assert {f["path"] for f in body["fields"]} >= {"header.supplier_gstin", "totals.grand_total"}


def test_rejects_missing_or_wrong_token(ok_client):
    assert post(ok_client, invoice_pdf(), token="wrong").status_code == 401


def test_fails_closed_without_configured_token():
    settings = replace(load_settings(), service_token=None, extract_model="gpt-6-luna")
    client = TestClient(create_app(settings, FakeLLMClient(lambda _r: raw_dict())))
    assert post(client, invoice_pdf()).status_code == 503


def test_bad_metadata_is_400(ok_client):
    response = post(ok_client, invoice_pdf(), metadata='{"attempt": 0}')
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_metadata"


def test_unsupported_file_is_422(ok_client):
    response = post(ok_client, b"just some text")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_type"


def test_budget_exceeded_is_429():
    def over_budget(_request):
        raise BudgetExceededError("Daily LLM budget reached")

    response = post(client_with(FakeLLMClient(over_budget)), invoice_pdf())
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "llm_budget_exceeded"
