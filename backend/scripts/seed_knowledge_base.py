"""Persist the curated Markdown knowledge base into PostgreSQL."""

import asyncio

from backend.app.db.session import SessionFactory
from backend.app.knowledge.loader import seed_knowledge_documents


async def main() -> None:
    async with SessionFactory() as session:
        count = await seed_knowledge_documents(session)
    print(f"Processed {count} knowledge documents.")


if __name__ == "__main__":
    asyncio.run(main())
