"""Model router — selects the cheapest capable model for each task.

The core of NunuClaw's cost-intelligence: complexity score → tier → provider.
Handles SLM→LLM escalation when a tier fails.
"""

from __future__ import annotations

import logging

from nunuclaw.config import NunuConfig
from nunuclaw.engine.models.base import BaseModelProvider, ModelResponse
from nunuclaw.engine.models.ollama import OllamaProvider
from nunuclaw.engine.models.groq import GroqProvider
from nunuclaw.engine.models.anthropic import AnthropicProvider

logger = logging.getLogger(__name__)

# Complexity score → recommended tier
TIER_MAPPING = {
    range(1, 4): 1,   # Score 1-3 → Tier 1 (Local SLM)
    range(4, 6): 2,   # Score 4-5 → Tier 2 (Fast Cloud)
    range(6, 9): 3,   # Score 6-8 → Tier 3 (Standard LLM)
    range(9, 11): 4,  # Score 9-10 → Tier 4 (Premium LLM)
}


def score_to_tier(complexity_score: int) -> int:
    """Convert a complexity score (1-10) to a model tier (1-4)."""
    score = max(1, min(10, complexity_score))
    for score_range, tier in TIER_MAPPING.items():
        if score in score_range:
            return tier
    return 3  # Default to standard LLM


class ModelRouter:
    """Routes tasks to the cheapest capable model.

    Manages provider instances and handles SLM→LLM escalation.
    """

    def __init__(self, config: NunuConfig) -> None:
        self.config = config
        self._providers: dict[int, BaseModelProvider] = {}
        self._total_cost: float = 0.0
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize model providers for each configured tier."""
        # Tier 1: Local SLM
        self._providers[1] = OllamaProvider(model=self.config.tier1.model)

        # Tier 2: Fast cloud
        if self.config.tier2.provider == "groq":
            self._providers[2] = GroqProvider(model=self.config.tier2.model)
        else:
            self._providers[2] = AnthropicProvider(model="claude-haiku-4-5-20251001")

        # Tier 3: Standard LLM
        self._providers[3] = AnthropicProvider(model=self.config.tier3.model)

        # Tier 4: Premium LLM
        self._providers[4] = AnthropicProvider(model=self.config.tier4.model)

    def get_provider(self, tier: int) -> BaseModelProvider | None:
        """Get the provider for a specific tier."""
        return self._providers.get(tier)

    async def generate(
        self,
        prompt: str,
        complexity_score: int = 5,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        max_escalations: int = 2,
    ) -> ModelResponse:
        """Generate text using the cheapest capable model.

        Starts at the recommended tier for the given complexity score,
        then escalates to higher tiers on failure.

        Args:
            prompt: The user/task prompt.
            complexity_score: Score 1-10 determining initial tier.
            system: Optional system prompt.
            max_tokens: Maximum response tokens.
            temperature: Creativity level.
            max_escalations: Maximum number of tier escalations.
        """
        start_tier = score_to_tier(complexity_score)
        current_tier = start_tier
        last_error = ""

        for attempt in range(max_escalations + 1):
            provider = self._providers.get(current_tier)
            if not provider:
                current_tier = min(current_tier + 1, 4)
                continue

            logger.info(
                f"Attempting tier {current_tier} ({provider.provider_name}) "
                f"for complexity {complexity_score}"
            )

            response = await provider.generate(
                prompt=prompt,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if response.success:
                self._total_cost += response.cost_usd
                logger.info(
                    f"Tier {current_tier} succeeded. "
                    f"Cost: ${response.cost_usd:.6f}, "
                    f"Tokens: {response.input_tokens}+{response.output_tokens}"
                )
                return response

            # Failed — escalate
            last_error = response.error or "Unknown error"
            logger.warning(f"Tier {current_tier} failed: {last_error}")

            if current_tier >= 4:
                break

            current_tier = min(current_tier + 1, 4)

        # All tiers failed
        return ModelResponse(
            success=False,
            error=f"All model tiers failed. Last error: {last_error}",
            provider="router",
            model="none",
        )

    async def classify(
        self,
        text: str,
        categories: list[str],
        complexity_score: int = 3,
        system: str = "",
    ) -> ModelResponse:
        """Classify text using the cheapest available model."""
        tier = score_to_tier(complexity_score)
        provider = self._providers.get(tier)

        if provider:
            response = await provider.classify(text, categories, system)
            if response.success:
                self._total_cost += response.cost_usd
                return response

        # Escalate through tiers
        for t in range(tier + 1, 5):
            provider = self._providers.get(t)
            if provider:
                response = await provider.classify(text, categories, system)
                if response.success:
                    self._total_cost += response.cost_usd
                    return response

        return ModelResponse(success=False, error="No model available for classification")

    @property
    def total_cost(self) -> float:
        """Return total accumulated API cost in USD."""
        return self._total_cost

    def reset_cost(self) -> None:
        """Reset the cost counter."""
        self._total_cost = 0.0
