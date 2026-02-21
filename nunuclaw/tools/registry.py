"""Tool registry — manages discovery and access to all available tools."""

from __future__ import annotations

from nunuclaw.tools.base import BaseTool


class ToolRegistry:
    """Central registry for all NunuClaw tools.

    Tools register themselves here and can be looked up by name.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def list_tools_with_descriptions(self) -> dict[str, str]:
        """List all tools with their descriptions."""
        return {name: tool.description for name, tool in self._tools.items()}

    def register_defaults(self, workspace_path: str = "") -> None:
        """Register all default core tools.

        Args:
            workspace_path: The sandbox workspace directory for file operations.
        """
        from nunuclaw.tools.file_manager import FileManagerTool
        from nunuclaw.tools.calculator import CalculatorTool
        from nunuclaw.tools.web_search import WebSearchTool

        self.register(FileManagerTool(workspace_path=workspace_path))
        self.register(CalculatorTool())
        self.register(WebSearchTool())
