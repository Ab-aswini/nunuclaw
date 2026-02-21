"""Gateway router — manages channels and routes messages to the processing pipeline."""

from __future__ import annotations

from typing import Callable, Awaitable

from nunuclaw.config import NunuConfig
from nunuclaw.gateway.channels.base import BaseChannel
from nunuclaw.gateway.channels.cli import CLIChannel
from nunuclaw.gateway.message import UnifiedMessage


class Gateway:
    """Gateway manages all communication channels.

    It initializes enabled channels, routes incoming messages to
    the processing callback, and delivers responses back.
    """

    def __init__(self, config: NunuConfig) -> None:
        self.config = config
        self.channels: dict[str, BaseChannel] = {}
        self._init_channels()

    def _init_channels(self) -> None:
        """Initialize enabled channels based on config."""
        if self.config.cli.enabled:
            self.channels["cli"] = CLIChannel()

        # Telegram, WhatsApp, Web — added in later phases
        # if self.config.telegram.enabled:
        #     self.channels["telegram"] = TelegramChannel(self.config.telegram)

    def get_channel(self, name: str) -> BaseChannel | None:
        """Get a channel by name."""
        return self.channels.get(name)

    async def run_channel(
        self,
        channel_name: str,
        on_message: Callable[[UnifiedMessage], Awaitable[str]],
    ) -> None:
        """Run a channel's receive loop.

        For each incoming message, calls on_message and sends the result back.

        Args:
            channel_name: Which channel to run.
            on_message: Async callback that processes a message and returns response text.
        """
        channel = self.channels.get(channel_name)
        if not channel:
            raise ValueError(f"Channel '{channel_name}' not found or not enabled.")

        await channel.start()
        try:
            async for message in channel.receive():
                response = await on_message(message)
                await channel.send(message.user_id, response)
        finally:
            await channel.stop()

    async def send_to_channel(
        self,
        channel_name: str,
        user_id: str,
        text: str,
        files: list[str] | None = None,
    ) -> None:
        """Send a message to a specific channel."""
        channel = self.channels.get(channel_name)
        if channel:
            await channel.send(user_id, text, files)
