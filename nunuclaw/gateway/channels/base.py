"""Base channel interface — all channel implementations inherit from this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from nunuclaw.gateway.message import UnifiedMessage


class BaseChannel(ABC):
    """Abstract base for all communication channels.

    Each channel must:
    1. Convert its native messages to UnifiedMessage (receive)
    2. Format and deliver results back to the user (send)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the channel identifier (e.g., 'cli', 'telegram')."""
        ...

    @abstractmethod
    async def receive(self) -> AsyncIterator[UnifiedMessage]:
        """Yield normalized messages from the channel.

        This is an async generator — it yields messages as they arrive.
        For CLI, this reads from stdin. For Telegram, it processes bot updates.
        """
        ...
        yield  # type: ignore  # Make this a generator

    @abstractmethod
    async def send(self, user_id: str, text: str, files: list[str] | None = None) -> None:
        """Send a response back to the user via this channel.

        Args:
            user_id: The channel-specific user identifier.
            text: The formatted response text.
            files: Optional list of file paths to send as attachments.
        """
        ...

    async def start(self) -> None:
        """Start the channel (e.g., connect to API, open socket). Override if needed."""

    async def stop(self) -> None:
        """Stop the channel gracefully. Override if needed."""
