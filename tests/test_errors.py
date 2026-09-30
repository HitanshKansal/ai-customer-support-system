"""Tests for Phase 14 error handling."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.errors import register_exception_handlers
from backend.app.core.errors import ResourceNotFoundError, RetrievalError


def test_application_error_handler_returns_stable_shape() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/missing")
    async def missing() -> None:
        raise ResourceNotFoundError("Order was not found")

    with TestClient(app) as client:
        response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "resource_not_found", "message": "Order was not found"}
    }


def test_validation_error_is_safe_and_structured() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/items/{item_id}")
    async def item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    with TestClient(app) as client:
        response = client.get("/items/not-an-integer")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_retrieval_error_has_retryable_status() -> None:
    error = RetrievalError("Knowledge retrieval is temporarily unavailable.")

    assert error.status_code == 502
    assert error.code == "retrieval_failure"
