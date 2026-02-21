"""Ollama local SLM provider — Tier 1 (free, on-device).

Connects to Ollama running at http://localhost:11434.
Models: Gemma 2B, Phi-3 Mini, Qwen 2.5, etc.
"""

from __future__ import annotations

import os

import httpx

from nunuclaw.engine.models.base import BaseModelProvider, ModelResponse


class OllamaProvider(BaseModelProvider):
    """Local Ollama SLM provider — free, offline-capable."""

    def __init__(self, model: str = "gemma:2b") -> None:
        self.model = model
        self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ModelResponse:
        """Generate text using local Ollama model."""
        try:
            payload: dict = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            }
            if system:
                payload["system"] = system

            resp = await self._client.post("/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

            return ModelResponse(
                text=data.get("response", "").strip(),
                model=self.model,
                provider="ollama",
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                cost_usd=0.0,  # Local = free
                success=True,
            )
        except httpx.ConnectError:
            return ModelResponse(
                success=False,
                error="Ollama not running. Start with: ollama serve",
                provider="ollama",
                model=self.model,
            )
        except Exception as e:
            return ModelResponse(
                success=False,
                error=f"Ollama error: {e}",
                provider="ollama",
                model=self.model,
            )

    async def classify(
        self,
        text: str,
        categories: list[str],
        system: str = "",
    ) -> ModelResponse:
        """Classify text using Ollama model."""
        cats = ", ".join(categories)
        prompt = (
            f"Classify the following text into exactly one of these categories: {cats}\n\n"
            f"Text: {text}\n\n"
            f"Respond with ONLY the category name, nothing else."
        )
        return await self.generate(prompt, system=system, max_tokens=50, temperature=0.1)

    async def health_check(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            resp = await self._client.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False
