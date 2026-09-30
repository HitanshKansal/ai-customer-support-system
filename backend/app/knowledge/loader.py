"""Load curated Markdown documents into knowledge-document records."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import KnowledgeDocument


DEFAULT_KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[3] / "knowledge_base"


@dataclass(frozen=True)
class KnowledgeDocumentInput:
    """Normalized content ready to become a database document."""

    title: str
    source: str
    content: str
    metadata: dict[str, str]


def load_knowledge_documents(
    directory: Path = DEFAULT_KNOWLEDGE_BASE_DIR,
) -> list[KnowledgeDocumentInput]:
    """Read all Markdown knowledge documents in deterministic filename order."""

    documents: list[KnowledgeDocumentInput] = []
    for path in sorted(directory.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        first_line, _, _ = content.partition("\n")
        title = first_line.removeprefix("# ").strip()
        if not title:
            raise ValueError(f"Knowledge document has no title: {path}")

        documents.append(
            KnowledgeDocumentInput(
                title=title,
                source=path.relative_to(directory.parent).as_posix(),
                content=content,
                metadata={"format": "markdown", "category": path.stem},
            )
        )

    return documents


async def seed_knowledge_documents(
    session: AsyncSession,
    directory: Path = DEFAULT_KNOWLEDGE_BASE_DIR,
) -> int:
    """Insert or update curated documents, returning the number processed."""

    documents = load_knowledge_documents(directory)
    for document in documents:
        existing = await session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.source == document.source
            )
        )
        if existing is None:
            session.add(
                KnowledgeDocument(
                    title=document.title,
                    source=document.source,
                    content=document.content,
                    document_metadata=document.metadata,
                )
            )
        else:
            existing.title = document.title
            existing.content = document.content
            existing.document_metadata = document.metadata

    await session.commit()
    return len(documents)
