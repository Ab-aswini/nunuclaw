"""Base tool interface and ToolResult schema."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool = True
    data: Any = None
    error: str | None = None
    files: list[str] = field(default_factory=list)  # Created/modified files


class BaseTool(ABC):
    """Abstract base for all NunuClaw tools.

    Tools are the actions NunuClaw can take in the world — create files,
    search the web, run calculations, etc.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier (e.g., 'file_manager')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        ...

    @property
    def actions(self) -> list[str]:
        """List of available actions for this tool."""
        return []

    @abstractmethod
    async def execute(self, action: str, params: dict) -> ToolResult:
        """Execute an action with the given parameters.

        Args:
            action: The method name to call (e.g., 'create_file', 'search').
            params: Parameters for the action.

        Returns:
            ToolResult with success/failure status and data.
        """
        ...
