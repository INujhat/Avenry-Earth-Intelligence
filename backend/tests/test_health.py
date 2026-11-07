"""Exercise the health endpoint through the HTTP interface."""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_returns_successful_json():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
