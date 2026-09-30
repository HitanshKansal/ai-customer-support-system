"""Tests for Phase 7 chunking and grounded context construction."""

from backend.app.knowledge.rag import (
    build_grounded_prompt,
    build_context,
    chunk_text,
)
from backend.app.knowledge.search import SimilarityResult


def test_chunking_creates_overlap() -> None:
    chunks = chunk_text("one two three four five six seven eight", chunk_size=20, chunk_overlap=5)

    assert len(chunks) > 1
    assert chunks[0].content.split()[-1] in chunks[1].content.split()
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))


def test_context_includes_sources_and_respects_limit() -> None:
    first = SimilarityResult(
        chunk=type("Chunk", (), {"content": "Refunds take 5 to 10 business days."})(),
        similarity=0.92,
        source="knowledge_base/refund_policy.md",
    )
    second = SimilarityResult(
        chunk=type("Chunk", (), {"content": "This section should be truncated."})(),
        similarity=0.51,
        source="knowledge_base/faq.md",
    )

    context = build_context([first, second], max_chars=100)

    assert "refund_policy.md" in context
    assert "faq.md" not in context


def test_grounded_prompt_contains_question_and_context() -> None:
    prompt = build_grounded_prompt("When will my refund arrive?", "Refunds take 5 to 10 business days.")

    assert "When will my refund arrive?" in prompt
    assert "Refunds take 5 to 10 business days." in prompt
    assert "Do not invent policy details" in prompt
