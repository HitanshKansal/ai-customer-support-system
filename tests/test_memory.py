"""Tests for Phase 12 conversation memory helpers."""

import pytest

from backend.app.agent.memory import ConversationMemory, MemoryTurn
from backend.app.db.models import MessageRole


def test_memory_finds_last_order_number() -> None:
    turns = [
        MemoryTurn(MessageRole.USER, "My order ORD-100 is delayed."),
        MemoryTurn(MessageRole.ASSISTANT, "I will check it."),
        MemoryTurn(MessageRole.USER, "Actually, use order ORD-45821."),
    ]

    assert ConversationMemory.find_last_order_number(turns) == "ORD-45821"


def test_memory_requires_positive_recent_limit() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        ConversationMemory(recent_limit=0)
