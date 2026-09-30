"""Tests for post-roadmap authentication foundations."""

from uuid import uuid4

import jwt
import pytest

from backend.app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from backend.app.main import app


def test_password_hashing_does_not_store_plaintext() -> None:
    password = "correct horse battery staple"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong password", password_hash)


def test_access_token_contains_user_identity_and_role() -> None:
    user_id = uuid4()
    token = create_access_token(user_id, "customer")
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "customer"


def test_auth_routes_are_documented() -> None:
    paths = app.openapi()["paths"]

    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/auth/me" in paths
