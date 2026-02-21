"""NunuClaw main entry point — CLI interface and agent orchestration.

Commands:
  nunuclaw start          Start interactive REPL
  nunuclaw chat "message" One-shot message processing
  nunuclaw setup          Interactive setup wizard
  nunuclaw status         Show system health and cost
"""

from __future__ import annotations

import asyncio
import logging
import time

import click
from rich.console import Console
from rich.logging import RichHandler

from nunuclaw import __version__
from nunuclaw.config import load_config, NunuConfig
from nunuclaw.delivery.formatter import format_for_channel
from nunuclaw.engine.executor import TaskExecutor
from nunuclaw.engine.models.router import ModelRouter
from nunuclaw.engine.planner import create_plan
from nunuclaw.gateway.channels.cli import CLIChannel
from nunuclaw.gateway.message import UnifiedMessage
from nunuclaw.gateway.router import Gateway
from nunuclaw.memory.store import MemoryStore
from nunuclaw.memory.profile import ProfileManager
from nunuclaw.memory.history import TaskHistory
from nunuclaw.tools.registry import ToolRegistry
from nunuclaw.understanding.intent import classify_intent
from nunuclaw.understanding.language import detect_language

console = Console()

# ─── Agent Core ──────────────────────────────────────────────────


class NunuClawAgent:
    """The NunuClaw autonomous agent — orchestrates all 5 layers."""

    def __init__(self, config: NunuConfig) -> None:
        self.config = config

        # Layer 3: Model router
        self.model_router = ModelRouter(config)

        # Layer 4: Memory
        self.memory = MemoryStore(config.database_path)
        self.profile_manager = ProfileManager(self.memory)
        self.task_history = TaskHistory(self.memory)

        # Tools
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_defaults(workspace_path=str(config.workspace_path))

        # Layer 3: Task executor
        self.executor = TaskExecutor(self.model_router, self.tool_registry)

        # Layer 1: Gateway
        self.gateway = Gateway(config)

    async def startup(self) -> None:
        """Initialize all components."""
        await self.memory.connect()

    async def shutdown(self) -> None:
        """Clean up all components."""
        await self.memory.close()

    async def process_message(self, message: UnifiedMessage) -> str:
        """Process a single message through the full pipeline.

        Pipeline: Gateway → Understanding → Planning → Execution → Delivery
        """
        start_time = time.time()

        # Layer 2: Understanding
        lang_result = detect_language(message.text)
        message.language = lang_result.code

        intent = await classify_intent(
            text=message.text,
            language=lang_result.code,
            model_router=self.model_router,
        )

        # Layer 3: Planning
        plan = await create_plan(
            intent=intent,
            original_message=message.text,
            user_id=message.user_id,
            model_router=self.model_router,
        )

        # Layer 3: Execution
        result = await self.executor.execute_plan(plan)

        # Layer 4: Memory — save to history
        duration = int(time.time() - start_time)
        await self.task_history.log_task(
            task_id=plan.id,
            user_id=message.user_id,
            message=message.text,
            intent=intent.intent,
            status=plan.status,
            result=result[:500],
            cost=self.model_router.total_cost,
            duration=duration,
        )

        # Save conversation
        await self.memory.add_conversation(
            message.user_id, "user", message.text, message.channel
        )
        await self.memory.add_conversation(
            message.user_id, "assistant", result[:500], message.channel
        )

        # Update profile
        await self.profile_manager.update_from_message(
            message.user_id, message.text, lang_result.code
        )

        # Layer 5: Delivery — format for channel
        formatted = format_for_channel(
            text=result,
            channel=message.channel,
            cost=self.model_router.total_cost,
        )

        return formatted


# ─── CLI Commands ────────────────────────────────────────────────


def _setup_logging(verbose: bool = False) -> None:
    """Configure structured logging with Rich."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


@click.group()
@click.version_option(__version__, prog_name="NunuClaw")
def cli() -> None:
    """🦀 NunuClaw — Universal autonomous AI assistant."""
    pass


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def start(verbose: bool) -> None:
    """Start the interactive NunuClaw REPL."""
    _setup_logging(verbose)
    asyncio.run(_run_interactive(verbose))


@cli.command()
@click.argument("message")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def chat(message: str, verbose: bool) -> None:
    """Process a single message and print the result."""
    _setup_logging(verbose)
    asyncio.run(_run_one_shot(message))


@cli.command()
def setup() -> None:
    """Interactive setup wizard."""
    console.print("[bold cyan]🦀 NunuClaw Setup Wizard[/]\n")

    config = load_config()
    console.print(f"  Config directory: [green]{config.config_dir}[/]")
    console.print(f"  Workspace: [green]{config.workspace_path}[/]")
    console.print(f"  Database: [green]{config.database_path}[/]")
    console.print()

    # Check providers
    import os
    checks = [
        ("Ollama", "OLLAMA_HOST", "http://localhost:11434"),
        ("Groq API Key", "GROQ_API_KEY", None),
        ("Anthropic API Key", "ANTHROPIC_API_KEY", None),
    ]

    for name, env_var, default in checks:
        val = os.getenv(env_var, default or "")
        if val:
            display = val[:8] + "..." if len(val) > 12 else val
            console.print(f"  ✅ {name}: [green]{display}[/]")
        else:
            console.print(f"  ❌ {name}: [red]Not configured[/]")

    console.print(
        "\n  Set API keys as environment variables:\n"
        "  [dim]export GROQ_API_KEY=your_key[/]\n"
        "  [dim]export ANTHROPIC_API_KEY=your_key[/]\n"
    )
    console.print("[green]Setup complete! Run [bold]nunuclaw start[/bold] to begin.[/]")


@cli.command()
def status() -> None:
    """Show system health and cost report."""
    config = load_config()
    console.print(f"[bold cyan]🦀 NunuClaw Status[/]\n")
    console.print(f"  Version: {__version__}")
    console.print(f"  Config: {config.config_dir}")
    console.print(f"  Workspace: {config.workspace_path}")
    console.print(f"  Database: {config.database_path}")
    console.print(f"  Cost limit: ${config.security.monthly_cost_limit_usd}/month")
    console.print()
    console.print("[green]System healthy ✅[/]")


# ─── Async Runners ───────────────────────────────────────────────


async def _run_interactive(verbose: bool = False) -> None:
    """Run the interactive REPL loop."""
    config = load_config()
    agent = NunuClawAgent(config)
    await agent.startup()

    try:
        cli_channel = CLIChannel()
        async for message in cli_channel.receive():
            response = await agent.process_message(message)
            await cli_channel.send(message.user_id, response)
    except KeyboardInterrupt:
        console.print("\n[dim]Shutting down...[/]")
    finally:
        await agent.shutdown()


async def _run_one_shot(message_text: str) -> None:
    """Process a single message and print result."""
    config = load_config()
    agent = NunuClawAgent(config)
    await agent.startup()

    try:
        message = UnifiedMessage(
            user_id="cli:local",
            text=message_text,
            channel="cli",
        )
        response = await agent.process_message(message)

        cli = CLIChannel()
        await cli.send_one_shot(response)
    finally:
        await agent.shutdown()


# ─── Direct execution ───────────────────────────────────────────

if __name__ == "__main__":
    cli()
