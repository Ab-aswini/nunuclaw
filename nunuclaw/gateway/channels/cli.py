"""CLI channel — interactive terminal input/output using Rich."""

from __future__ import annotations

from typing import AsyncIterator

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from nunuclaw.gateway.channels.base import BaseChannel
from nunuclaw.gateway.message import UnifiedMessage

console = Console()


class CLIChannel(BaseChannel):
    """Command-line channel for developer testing and interactive use.

    Uses Rich for formatted output with colors and panels.
    """

    @property
    def name(self) -> str:
        return "cli"

    async def receive(self) -> AsyncIterator[UnifiedMessage]:
        """Read messages from stdin in a loop.

        Yields UnifiedMessage for each line of user input.
        Type 'exit' or 'quit' to stop. Ctrl+C also works.
        """
        console.print(
            Panel(
                Text.from_markup(
                    "[bold cyan]🦀 NunuClaw[/] v0.1.0 — "
                    "Type a message, or [bold]exit[/] to quit."
                ),
                border_style="cyan",
            )
        )
        while True:
            try:
                user_input = console.input("[bold green]you >[/] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Goodbye! 🦀[/]")
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
                console.print("[dim]Goodbye! 🦀[/]")
                break

            yield UnifiedMessage(
                user_id="cli:local",
                text=user_input,
                channel="cli",
            )

    async def send(self, user_id: str, text: str, files: list[str] | None = None) -> None:
        """Print the response to the terminal with Rich formatting."""
        console.print()
        console.print(
            Panel(
                Markdown(text),
                title="[bold cyan]🦀 NunuClaw[/]",
                border_style="blue",
                padding=(1, 2),
            )
        )

        if files:
            for f in files:
                console.print(f"  📎 [link=file://{f}]{f}[/link]")

        console.print()

    async def send_one_shot(self, text: str, files: list[str] | None = None) -> None:
        """Print a single response (for `nunuclaw chat` one-shot mode)."""
        console.print(Markdown(text))
        if files:
            for f in files:
                console.print(f"  📎 {f}")
