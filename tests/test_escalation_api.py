"""Tests for Phase 13 escalation API registration."""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_escalation_routes_are_documented() -> None:
    paths = app.openapi()["paths"]

    assert "/escalations" in paths
    assert "post" in paths["/escalations"]
    assert "/escalations/{escalation_id}" in paths
    assert "get" in paths["/escalations/{escalation_id}"]


def test_health_still_works_after_router_registration() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_escalation_validation_returns_structured_error() -> None:
    with TestClient(app) as client:
        response = client.post("/escalations", json={"reason": "Need help"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
