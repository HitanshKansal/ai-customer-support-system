"""Shared dependency factories for application services."""

from functools import lru_cache

from backend.app.agent.memory import ConversationMemory
from backend.app.agent.runtime import AgentDependencies, SupportAgent
from backend.app.knowledge.embeddings import EmbeddingService
from backend.app.knowledge.rag import RagService
from backend.app.llm.openai_compatible import OpenAICompatibleChatModel


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Create one process-wide embedding service and model instance."""

    return EmbeddingService()


@lru_cache
def get_chat_model() -> OpenAICompatibleChatModel:
    """Create one configured chat-model client."""

    return OpenAICompatibleChatModel()


@lru_cache
def get_support_agent() -> SupportAgent:
    """Create the production agent with RAG and conversation memory."""

    rag = RagService(get_embedding_service(), get_chat_model())
    return SupportAgent(
        AgentDependencies(rag=rag, memory=ConversationMemory())
    )
