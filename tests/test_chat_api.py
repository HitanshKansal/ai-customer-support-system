"""Tests for the authenticated chat API surface."""

from backend.app.main import app


def test_chat_route_is_documented() -> None:
    schema = app.openapi()
    path = schema["paths"]["/agent/chat"]

    assert "post" in path
    security_schemes = schema["components"]["securitySchemes"]
    assert "HTTPBearer" in security_schemes
    assert security_schemes["HTTPBearer"]["scheme"] == "bearer"
