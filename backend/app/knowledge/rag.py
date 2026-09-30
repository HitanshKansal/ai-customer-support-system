"""End-to-end retrieval-augmented generation building blocks."""

from dataclasses import dataclass
from typing import Protocol, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.errors import LLMError, RetrievalError
from backend.app.db.models import DocumentChunk, KnowledgeDocument
from backend.app.knowledge.embeddings import EmbeddingService
from backend.app.knowledge.loader import KnowledgeDocumentInput
from backend.app.knowledge.search import SimilarityResult, search_similar_chunks


@dataclass(frozen=True)
class TextChunk:
    """A bounded section of a source document."""

    index: int
    content: str


@dataclass(frozen=True)
class EmbeddedChunk:
    """A text chunk paired with its embedding."""

    index: int
    content: str
    embedding: list[float]


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[TextChunk]:
    """Split text into overlapping character-bounded chunks."""

    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between 0 and chunk_size")

    normalized = " ".join(text.split())
    chunks: list[TextChunk] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        content = normalized[start:end].strip()
        if content:
            chunks.append(TextChunk(index=len(chunks), content=content))

        if end >= len(normalized):
            break
        start = end - chunk_overlap
        while start < len(normalized) and normalized[start].isspace():
            start += 1

    return chunks


def embed_document_chunks(
    document: KnowledgeDocumentInput,
    embedding_service: EmbeddingService,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[EmbeddedChunk]:
    """Chunk one document and embed every chunk with the same model."""

    chunks = chunk_text(document.content, chunk_size, chunk_overlap)
    vectors = embedding_service.embed_texts([chunk.content for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("Embedding provider returned the wrong number of vectors")

    return [
        EmbeddedChunk(index=chunk.index, content=chunk.content, embedding=vector)
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]


async def ingest_knowledge_documents(
    session: AsyncSession,
    documents: Sequence[KnowledgeDocumentInput],
    embedding_service: EmbeddingService,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> int:
    """Upsert documents and replace their chunks and embeddings transactionally."""

    processed = 0
    for source_document in documents:
        document = await session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.source == source_document.source
            )
        )
        if document is None:
            document = KnowledgeDocument(
                title=source_document.title,
                source=source_document.source,
                content=source_document.content,
                document_metadata=source_document.metadata,
            )
            session.add(document)
            await session.flush()
        else:
            document.title = source_document.title
            document.content = source_document.content
            document.document_metadata = source_document.metadata
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
            )

        embedded_chunks = embed_document_chunks(
            source_document,
            embedding_service,
            chunk_size,
            chunk_overlap,
        )
        session.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    embedding=chunk.embedding,
                )
                for chunk in embedded_chunks
            ]
        )
        processed += 1

    await session.commit()
    return processed


def build_context(results: Sequence[SimilarityResult], max_chars: int = 6000) -> str:
    """Format retrieved chunks as attributed context for an LLM prompt."""

    if max_chars < 1:
        raise ValueError("max_chars must be at least 1")

    sections: list[str] = []
    current_length = 0
    for result in results:
        section = (
            f"[Source: {result.source}; similarity: {result.similarity:.3f}]\n"
            f"{result.chunk.content}"
        )
        separator_length = 2 if sections else 0
        if current_length + separator_length + len(section) > max_chars:
            break
        sections.append(section)
        current_length += separator_length + len(section)

    return "\n\n".join(sections)


def build_grounded_prompt(question: str, context: str) -> str:
    """Create an instruction that restricts answers to retrieved context."""

    return (
        "You are a customer support assistant. Answer using only the provided "
        "context. If the context does not contain the answer, say that you do "
        "not have enough information and recommend human support. Do not invent "
        "policy details.\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}"
    )


class ChatModel(Protocol):
    """Interface for a chat model used after retrieval."""

    async def generate(self, prompt: str) -> str:
        """Generate a response from a grounded prompt."""


@dataclass(frozen=True)
class RagResponse:
    """Answer text together with the sources used to create it."""

    answer: str
    sources: list[str]


class RagService:
    """Coordinate query embedding, retrieval, context injection, and generation."""

    def __init__(self, embedding_service: EmbeddingService, chat_model: ChatModel):
        self.embedding_service = embedding_service
        self.chat_model = chat_model

    async def answer(
        self,
        session: AsyncSession,
        question: str,
        top_k: int = 5,
    ) -> RagResponse:
        """Return a grounded answer and the source paths retrieved."""

        try:
            query_vector = self.embedding_service.embed_query(question)
            results = await search_similar_chunks(session, query_vector, top_k)
        except Exception as exc:
            raise RetrievalError(
                "Knowledge retrieval is temporarily unavailable."
            ) from exc
        context = build_context(results)
        prompt = build_grounded_prompt(question, context)
        try:
            answer = await self.chat_model.generate(prompt)
        except Exception as exc:
            raise LLMError(
                "The assistant could not generate a response right now."
            ) from exc
        return RagResponse(answer=answer, sources=[result.source for result in results])
