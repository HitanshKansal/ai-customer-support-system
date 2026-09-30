"""Failure-path tests for agent and RAG services."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.app.agent.runtime import AgentDependencies, AgentRequest, SupportAgent
from backend.app.agent.tools import (
    CheckOrderStatusInput,
    OrderStatusResult,
    ToolNotFoundError,
)
from backend.app.core.errors import LLMError, RetrievalError
from backend.app.knowledge.embeddings import EmbeddingService
from backend.app.knowledge.rag import RagService


class FakeRag:
    async def answer(self, session, question):
        return type("Result", (), {"answer": "ok", "sources": []})()


async def missing_order(session, request: CheckOrderStatusInput):
    raise ToolNotFoundError("No order was found")


@pytest.mark.asyncio
async def test_agent_converts_missing_tool_data_to_safe_response() -> None:
    agent = SupportAgent(
        AgentDependencies(rag=FakeRag(), check_order=missing_order)
    )

    response = await agent.handle(
        None,
        AgentRequest(user_message="Where is order ORD-404?", customer_id=uuid4()),
    )

    assert response.route == "error"
    assert response.error_code == "resource_not_found"
    assert "could not find" in response.answer


class FakeEmbeddingService:
    def embed_query(self, question: str) -> list[float]:
        return [0.1]


class FailingChatModel:
    async def generate(self, prompt: str) -> str:
        raise RuntimeError("provider unavailable")


@pytest.mark.asyncio
async def test_rag_wraps_retrieval_failures(monkeypatch) -> None:
    async def fail_search(session, query_vector, top_k):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("backend.app.knowledge.rag.search_similar_chunks", fail_search)
    service = RagService(FakeEmbeddingService(), FailingChatModel())

    with pytest.raises(RetrievalError):
        await service.answer(None, "What is the refund policy?")


@pytest.mark.asyncio
async def test_rag_wraps_llm_failures(monkeypatch) -> None:
    async def empty_search(session, query_vector, top_k):
        return []

    monkeypatch.setattr("backend.app.knowledge.rag.search_similar_chunks", empty_search)
    service = RagService(FakeEmbeddingService(), FailingChatModel())

    with pytest.raises(LLMError):
        await service.answer(None, "What is the refund policy?")
