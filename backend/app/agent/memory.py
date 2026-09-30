"""Persistent conversation memory and short-term context helpers."""

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ConversationMessage, MessageRole


@dataclass(frozen=True)
class MemoryTurn:
    """A prompt-ready conversation turn."""

    role: MessageRole
    content: str


class ConversationMemory:
    """Store conversation turns and load a bounded recent session window."""

    def __init__(self, recent_limit: int = 12):
        if recent_limit < 1:
            raise ValueError("recent_limit must be at least 1")
        self.recent_limit = recent_limit

    async def load_recent(
        self,
        session: AsyncSession,
        conversation_id: UUID,
    ) -> list[MemoryTurn]:
        """Load recent turns in chronological order for prompt construction."""

        result = await session.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(self.recent_limit)
        )
        messages = list(result)
        messages.reverse()
        return [MemoryTurn(role=message.role, content=message.content) for message in messages]

    async def record_exchange(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        customer_id: UUID,
        user_message: str,
        assistant_message: str,
        ticket_id: UUID | None = None,
    ) -> None:
        """Persist one user turn and its assistant response atomically."""

        session.add_all(
            [
                ConversationMessage(
                    session_id=conversation_id,
                    ticket_id=ticket_id,
                    author_id=customer_id,
                    role=MessageRole.USER,
                    content=user_message,
                ),
                ConversationMessage(
                    session_id=conversation_id,
                    ticket_id=ticket_id,
                    role=MessageRole.ASSISTANT,
                    content=assistant_message,
                ),
            ]
        )
        await session.commit()

    @staticmethod
    def find_last_order_number(turns: list[MemoryTurn]) -> str | None:
        """Find the most recently mentioned order number in a session window."""

        pattern = re.compile(r"\b(?:order|ord)\s*[-:#]?\s*([A-Za-z0-9-]+)", re.I)
        for turn in reversed(turns):
            match = pattern.search(turn.content)
            if match:
                return match.group(1)
        return None
