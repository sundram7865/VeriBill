from fastapi.testclient import TestClient

from extractor.main import create_app


def test_health_reports_status_and_tesseract():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "tesseract" in body
