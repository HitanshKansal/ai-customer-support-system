"""Tests for Phase 5 embedding behavior without loading a model."""

import pytest

from backend.app.knowledge.embeddings import EmbeddingService, cosine_similarity
from backend.app.knowledge.loader import KnowledgeDocumentInput


class FakeEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]


def test_embedding_service_preserves_document_sources() -> None:
    documents = [
        KnowledgeDocumentInput(
            title="FAQ",
            source="knowledge_base/faq.md",
            content="How can I contact support?",
            metadata={"category": "faq"},
        )
    ]

    embedded = EmbeddingService(FakeEmbeddingProvider()).embed_documents(documents)

    assert embedded[0].document.source == "knowledge_base/faq.md"
    assert embedded[0].vector == [26.0, 1.0]


def test_cosine_similarity_is_one_for_identical_vectors() -> None:
    assert cosine_similarity([3.0, 4.0], [3.0, 4.0]) == pytest.approx(1.0)


def test_cosine_similarity_rejects_mismatched_dimensions() -> None:
    with pytest.raises(ValueError, match="same dimension"):
        cosine_similarity([1.0, 2.0], [1.0])
