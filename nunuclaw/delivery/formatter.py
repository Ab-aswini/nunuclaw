"""Delivery formatter — format results per channel."""

from __future__ import annotations


def format_for_channel(text: str, channel: str, cost: float = 0.0) -> str:
    """Format a response for the given channel.

    Args:
        text: The raw response text.
        channel: Target channel ('cli', 'telegram', 'web', etc.)
        cost: API cost for this response (appended as footer if > 0).

    Returns:
        Formatted text appropriate for the channel.
    """
    if not text:
        return "No response generated."

    formatted = text.strip()

    # Add cost footer if applicable
    if cost > 0.001:
        if channel == "cli":
            formatted += f"\n\n_Cost: ${cost:.4f}_"
        elif channel == "telegram":
            formatted += f"\n\n💰 Cost: ${cost:.4f}"

    return formatted
