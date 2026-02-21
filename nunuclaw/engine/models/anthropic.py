"""Anthropic Claude provider — Tier 3-4 (Haiku, Sonnet, Opus).

Uses the official anthropic SDK for reliable API access.
"""

from __future__ import annotations

import os

from nunuclaw.engine.models.base import BaseModelProvider, ModelResponse

# Pricing per token (as of 2026 — approximate)
_PRICING: dict[str, tuple[float, float]] = {
    # (input_cost_per_token, output_cost_per_token)
    "claude-haiku-4-5-20251001": (0.25 / 1_000_000, 1.25 / 1_000_000),
    "claude-sonnet-4-5-20250929": (3.0 / 1_000_000, 15.0 / 1_000_000),
    "claude-opus-4-6": (15.0 / 1_000_000, 75.0 / 1_000_000),
}

# Default fallback pricing
_DEFAULT_PRICING = (3.0 / 1_000_000, 15.0 / 1_000_000)


class AnthropicProvider(BaseModelProvider):
    """Anthropic Claude provider — Haiku (cheap), Sonnet (balanced), Opus (premium)."""

    def __init__(self, model: str = "claude-sonnet-4-5-20250929") -> None:
        self.model = model
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._client = None

    def _get_client(self):
        """Lazy-init the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
        return self._client

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ModelResponse:
        """Generate text using Claude API."""
        if not self.api_key:
            return ModelResponse(
                success=False,
                error="ANTHROPIC_API_KEY not set. Get one at https://console.anthropic.com/",
                provider="anthropic",
                model=self.model,
            )

        try:
            client = self._get_client()

            kwargs: dict = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            }
            if system:
                kwargs["system"] = system

            response = await client.messages.create(**kwargs)

            # Extract text from response
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            # Calculate cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            in_cost, out_cost = _PRICING.get(self.model, _DEFAULT_PRICING)
            cost = (input_tokens * in_cost) + (output_tokens * out_cost)

            return ModelResponse(
                text=text.strip(),
                model=self.model,
                provider="anthropic",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                success=True,
            )
        except Exception as e:
            return ModelResponse(
                success=False,
                error=f"Anthropic error: {e}",
                provider="anthropic",
                model=self.model,
            )

    async def classify(
        self,
        text: str,
        categories: list[str],
        system: str = "",
    ) -> ModelResponse:
        """Classify text using Claude."""
        cats = ", ".join(categories)
        prompt = (
            f"Classify the following text into exactly one of these categories: {cats}\n\n"
            f"Text: {text}\n\n"
            f"Respond with ONLY the category name, nothing else."
        )
        return await self.generate(prompt, system=system, max_tokens=50, temperature=0.1)
