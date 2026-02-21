"""Base model provider interface and response schema."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ModelResponse:
    """Response from an AI model provider."""

    text: str = ""
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    success: bool = True
    error: str | None = None


class BaseModelProvider(ABC):
    """Abstract base for all AI model providers.

    Providers wrap model APIs (Ollama, Groq, Anthropic) and
    expose a uniform generate/classify interface.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return identifier for this provider (e.g., 'ollama', 'groq', 'anthropic')."""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ModelResponse:
        """Generate text from a prompt.

        Args:
            prompt: The user/task prompt.
            system: Optional system prompt for context.
            max_tokens: Maximum tokens in response.
            temperature: Creativity level (0.0 = deterministic, 1.0 = creative).
        """
        ...

    @abstractmethod
    async def classify(
        self,
        text: str,
        categories: list[str],
        system: str = "",
    ) -> ModelResponse:
        """Classify text into one of the given categories.

        Returns a ModelResponse where .text is the selected category.
        """
        ...

    async def health_check(self) -> bool:
        """Check if the provider is available and responding.

        Returns True if the provider is ready, False otherwise.
        """
        try:
            resp = await self.generate("Say 'ok'.", max_tokens=10)
            return resp.success
        except Exception:
            return False
