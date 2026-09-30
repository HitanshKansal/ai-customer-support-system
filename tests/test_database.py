"""Tests for Phase 2 database configuration."""

from sqlalchemy.engine import make_url

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db import models  # noqa: F401
from backend.app.db.session import engine


def test_database_engine_uses_async_postgresql() -> None:
    database_url = make_url(get_settings().database_url)

    assert database_url.drivername == "postgresql+asyncpg"
    assert engine.url.drivername == "postgresql+asyncpg"


def test_core_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "tickets",
        "orders",
        "payments",
        "conversation_messages",
        "escalations",
        "knowledge_documents",
        "document_chunks",
    }


def test_ticket_has_customer_and_optional_agent_relationships() -> None:
    ticket_columns = Base.metadata.tables["tickets"].c

    assert ticket_columns.customer_id.nullable is False
    assert ticket_columns.assigned_agent_id.nullable is True
