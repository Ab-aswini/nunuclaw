"""Groq API provider — Tier 2 (fast cloud SLM, generous free tier).

Uses OpenAI-compatible chat completions endpoint.
"""

from __future__ import annotations

import os

import httpx

from nunuclaw.engine.models.base import BaseModelProvider, ModelResponse

# Groq pricing per 1M tokens (approximate for Llama 3.1 8B)
_GROQ_INPUT_COST = 0.05 / 1_000_000   # $0.05 per 1M input tokens
_GROQ_OUTPUT_COST = 0.08 / 1_000_000  # $0.08 per 1M output tokens


class GroqProvider(BaseModelProvider):
    """Groq cloud provider — fast inference, generous free tier."""

    def __init__(self, model: str = "llama-3.1-8b-instant") -> None:
        self.model = model
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self._client = httpx.AsyncClient(
            base_url="https://api.groq.com/openai/v1",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    @property
    def provider_name(self) -> str:
        return "groq"

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ModelResponse:
        """Generate text using Groq API."""
        if not self.api_key:
            return ModelResponse(
                success=False,
                error="GROQ_API_KEY not set. Get one at https://console.groq.com/keys",
                provider="groq",
                model=self.model,
            )

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            resp = await self._client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = (input_tokens * _GROQ_INPUT_COST) + (output_tokens * _GROQ_OUTPUT_COST)

            text = data["choices"][0]["message"]["content"].strip()

            return ModelResponse(
                text=text,
                model=self.model,
                provider="groq",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                success=True,
            )
        except httpx.HTTPStatusError as e:
            return ModelResponse(
                success=False,
                error=f"Groq API error {e.response.status_code}: {e.response.text[:200]}",
                provider="groq",
                model=self.model,
            )
        except Exception as e:
            return ModelResponse(
                success=False,
                error=f"Groq error: {e}",
                provider="groq",
                model=self.model,
            )

    async def classify(
        self,
        text: str,
        categories: list[str],
        system: str = "",
    ) -> ModelResponse:
        """Classify text using Groq model."""
        cats = ", ".join(categories)
        prompt = (
            f"Classify the following text into exactly one of these categories: {cats}\n\n"
            f"Text: {text}\n\n"
            f"Respond with ONLY the category name, nothing else."
        )
        return await self.generate(prompt, system=system, max_tokens=50, temperature=0.1)
