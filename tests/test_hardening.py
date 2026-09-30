"""Tests for HTTP hardening and request observability."""

from fastapi.testclient import TestClient

from backend.app.core.middleware import FixedWindowRateLimiter
from backend.app.main import app


def test_health_response_has_security_and_request_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_request_id_is_preserved() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "demo-request"})

    assert response.headers["x-request-id"] == "demo-request"


def test_rate_limiter_rejects_after_limit() -> None:
    limiter = FixedWindowRateLimiter(lambda *_args: None, max_requests=1, window_seconds=60)

    assert limiter._allowed("client", "/auth/login", now=10)
    assert not limiter._allowed("client", "/auth/login", now=11)
    assert limiter._allowed("client", "/auth/login", now=71)
