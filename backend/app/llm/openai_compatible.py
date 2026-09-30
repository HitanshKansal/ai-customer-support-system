"""OpenAI-compatible chat completion provider."""

import httpx

from backend.app.core.config import get_settings
from backend.app.core.errors import LLMError


class OpenAICompatibleChatModel:
    """Call a configurable OpenAI-compatible chat completion endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 45.0,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.model = model or settings.llm_model
        self.timeout_seconds = timeout_seconds

    async def generate(self, prompt: str) -> str:
        """Generate one response or raise a safe provider error."""

        if not self.api_key:
            raise LLMError("The LLM provider is not configured.")

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
        except LLMError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("The LLM provider is temporarily unavailable.") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMError("The LLM provider returned an empty response.")
        return content.strip()
