"""Tests for the Phase 1 health endpoint."""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "AI Customer Support API"
