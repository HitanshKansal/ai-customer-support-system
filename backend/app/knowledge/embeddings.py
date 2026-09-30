"""Embedding generation and cosine-similarity utilities."""

from dataclasses import dataclass
from math import sqrt
from typing import Protocol, Sequence

from backend.app.core.config import get_settings
from backend.app.knowledge.loader import KnowledgeDocumentInput


class EmbeddingProvider(Protocol):
    """Minimal interface implemented by concrete embedding providers."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector for each input text."""


class SentenceTransformerProvider:
    """Lazy wrapper around a local sentence-transformers model."""

    def __init__(self, model_name: str | None = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required to generate embeddings"
            ) from exc

        selected_model = model_name or get_settings().embedding_model
        self.model = SentenceTransformer(selected_model)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Encode texts as normalized Python lists."""

        vectors = self.model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [vector.tolist() for vector in vectors]


@dataclass(frozen=True)
class EmbeddedDocument:
    """A source document paired with its in-memory embedding."""

    document: KnowledgeDocumentInput
    vector: list[float]


class EmbeddingService:
    """Generate vectors for documents and user queries."""

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self.provider = provider or SentenceTransformerProvider()

    def embed_documents(
        self, documents: Sequence[KnowledgeDocumentInput]
    ) -> list[EmbeddedDocument]:
        """Embed document content while preserving source metadata."""

        vectors = self.provider.embed([document.content for document in documents])
        if len(vectors) != len(documents):
            raise ValueError("Embedding provider returned the wrong number of vectors")

        return [
            EmbeddedDocument(document=document, vector=vector)
            for document, vector in zip(documents, vectors, strict=True)
        ]

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed arbitrary text segments such as document chunks."""

        return self.provider.embed(list(texts))

    def embed_query(self, query: str) -> list[float]:
        """Embed one user question using the same model as documents."""

        vectors = self.embed_texts([query])
        if len(vectors) != 1:
            raise ValueError("Embedding provider must return one query vector")
        return vectors[0]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Calculate cosine similarity for two vectors of equal dimension."""

    if len(left) != len(right):
        raise ValueError("Vectors must have the same dimension")

    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("Cosine similarity is undefined for a zero vector")

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
    return dot_product / (left_norm * right_norm)
