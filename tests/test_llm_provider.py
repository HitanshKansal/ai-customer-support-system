"""Tests for the configurable chat-model adapter."""

import pytest

from backend.app.core.errors import LLMError
from backend.app.llm.openai_compatible import OpenAICompatibleChatModel


@pytest.mark.asyncio
async def test_provider_requires_api_key() -> None:
    provider = OpenAICompatibleChatModel(api_key=None)

    with pytest.raises(LLMError, match="not configured"):
        await provider.generate("Hello")
