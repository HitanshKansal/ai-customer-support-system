"""Vector storage and similarity search helpers."""

from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.db.models import DocumentChunk, KnowledgeDocument


@dataclass(frozen=True)
class SimilarityResult:
    """A chunk and its cosine similarity to the query vector."""

    chunk: DocumentChunk
    similarity: float
    source: str


def validate_vector(vector: Sequence[float]) -> list[float]:
    """Validate and normalize a vector for the configured pgvector dimension."""

    values = [float(value) for value in vector]
    expected_dimension = get_settings().embedding_dimension
    if len(values) != expected_dimension:
        raise ValueError(
            f"Expected an embedding with {expected_dimension} dimensions, "
            f"received {len(values)}"
        )
    return values


def build_similarity_query(
    query_vector: Sequence[float], top_k: int = 5
) -> Select[tuple[DocumentChunk, str, float]]:
    """Build a PostgreSQL cosine-distance query for embedded chunks."""

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    vector = validate_vector(query_vector)
    distance = DocumentChunk.embedding.cosine_distance(vector)
    similarity = (1 - distance).label("similarity")
    return (
        select(DocumentChunk, KnowledgeDocument.source, similarity)
        .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    )


async def search_similar_chunks(
    session: AsyncSession,
    query_vector: Sequence[float],
    top_k: int = 5,
) -> list[SimilarityResult]:
    """Return the closest embedded chunks ordered by cosine similarity."""

    result = await session.execute(build_similarity_query(query_vector, top_k))
    return [
        SimilarityResult(
            chunk=chunk,
            similarity=float(similarity),
            source=source,
        )
        for chunk, source, similarity in result.all()
    ]


async def save_chunk_embedding(
    session: AsyncSession,
    chunk_id: UUID,
    vector: Sequence[float],
) -> DocumentChunk:
    """Store one validated embedding on an existing document chunk."""

    chunk = await session.get(DocumentChunk, chunk_id)
    if chunk is None:
        raise ValueError(f"Document chunk not found: {chunk_id}")

    chunk.embedding = validate_vector(vector)
    await session.commit()
    await session.refresh(chunk)
    return chunk
